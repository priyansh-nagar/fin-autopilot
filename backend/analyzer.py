"""
analyzer.py – Core analysis engine.
Detects: duplicate vendors, transaction anomalies, budget variance,
         procurement overpricing, cloud cost spikes.
Applies false-positive filters and attaches confidence scores.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

from cleaner import clean_numeric, normalize_vendor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Benchmark prices (INR)
# ---------------------------------------------------------------------------

BENCHMARKS: dict[str, float] = {
    "laptop": 67_500, "desktop": 45_000, "monitor": 28_500,
    "server": 280_000, "printer": 44_500, "ups": 21_000,
    "chair": 16_200, "paper_ream": 285, "toner": 2_850,
    "zoom_seat": 10_800, "slack_seat": 6_250, "salesforce_seat": 98_500,
    "aws_reserved_1yr": 154_000, "diesel_litre": 94, "water_can": 72,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_col(df: pd.DataFrame, *candidates: str) -> str | None:
    for cand in candidates:
        for col in df.columns:
            if cand in col.lower():
                return col
    return None


def _numeric_col(df: pd.DataFrame, col: str | None) -> pd.Series:
    if col is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce").fillna(0)


def _text_col(df: pd.DataFrame, col: str | None, default: str = "") -> pd.Series:
    if col is None:
        return pd.Series([default] * len(df))
    return df[col].fillna(default).astype(str)


def _anomaly(
    atype: str,
    description: str,
    impact: float,
    confidence: float,
    reason: str,
    recommendation: str,
    source_rows: list[int] | None = None,
    false_positive: bool = False,
) -> dict[str, Any]:
    return {
        "type": atype,
        "description": description,
        "impact": round(impact, 2),
        "confidence": round(min(max(confidence, 0.0), 1.0), 2),
        "reason": reason,
        "recommendation": recommendation,
        "source_rows": source_rows or [],
        "false_positive": false_positive,
    }


# ---------------------------------------------------------------------------
# False-positive detection helpers
# ---------------------------------------------------------------------------

_INTERNAL_KEYWORDS = re.compile(
    r"\b(internal|recharge|transfer|intercompany|reversal|correction)\b", re.I
)


def _is_recurring(amounts: pd.Series, amount: float, tolerance: float = 0.01) -> bool:
    """Return True if amount appears 3+ times (likely subscription)."""
    matches = (amounts - amount).abs() <= tolerance * amount
    return int(matches.sum()) >= 3


def _is_internal(text: str) -> bool:
    return bool(_INTERNAL_KEYWORDS.search(text))


# ---------------------------------------------------------------------------
# A. Duplicate Vendor Detection
# ---------------------------------------------------------------------------

def detect_duplicate_vendors(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """
    Returns (anomalies, duplicate_vendor_groups).
    Groups vendors by normalized name, flags when same tax-id appears on
    multiple entries or when fuzzy name similarity is high.
    """
    anomalies: list[dict] = []
    groups: list[dict] = []

    vendor_col = _find_col(df, "vendor", "supplier", "name", "party")
    amount_col = _find_col(df, "amount", "invoice", "total", "value", "spend", "cost")
    tax_col = _find_col(df, "gstin", "pan", "tax_id", "gst")

    if vendor_col is None:
        logger.warning("duplicate_vendors: no vendor column found")
        return anomalies, groups

    amounts = _numeric_col(df, amount_col)
    vendors_raw = _text_col(df, vendor_col)
    vendors_norm = vendors_raw.apply(normalize_vendor)
    tax_ids = _text_col(df, tax_col) if tax_col else pd.Series([""] * len(df))

    # Group by normalized name
    name_groups: dict[str, list[int]] = defaultdict(list)
    for idx, norm in vendors_norm.items():
        if norm:
            name_groups[norm].append(int(idx))

    for norm_name, idxs in name_groups.items():
        if len(idxs) < 2:
            continue
        raw_names = vendors_raw.iloc[idxs].unique().tolist()
        total_amount = float(amounts.iloc[idxs].sum())
        group_tax = tax_ids.iloc[idxs].unique().tolist()

        # Skip internal transfers
        if any(_is_internal(n) for n in raw_names):
            continue

        confidence = min(0.5 + 0.1 * len(idxs), 0.95)
        description = (
            f"Vendor '{raw_names[0]}' appears under {len(raw_names)} name variants: "
            + ", ".join(f'"{n}"' for n in raw_names[:5])
        )
        impact = total_amount * 0.05  # 5% duplicate overhead estimate

        anomalies.append(_anomaly(
            atype="duplicate_vendor",
            description=description,
            impact=impact,
            confidence=confidence,
            reason=f"Normalized name '{norm_name}' matches {len(idxs)} rows with variants in vendor names.",
            recommendation="Consolidate vendor master entries; enforce unique PAN/GSTIN check at invoice entry.",
            source_rows=idxs,
        ))
        groups.append({
            "normalized_name": norm_name,
            "variants": raw_names,
            "row_count": len(idxs),
            "total_spend": round(total_amount, 2),
            "tax_ids": [t for t in group_tax if t and t != "nan"],
        })

    # Same tax-ID, different names
    if tax_col:
        tax_groups: dict[str, list[int]] = defaultdict(list)
        for idx, tid in tax_ids.items():
            if tid and tid not in ("", "nan", "None"):
                tax_groups[tid].append(int(idx))
        for tid, idxs in tax_groups.items():
            if len(idxs) < 2:
                continue
            raw_names = vendors_raw.iloc[idxs].unique().tolist()
            if len(raw_names) < 2:
                continue
            total_amount = float(amounts.iloc[idxs].sum())
            anomalies.append(_anomaly(
                atype="duplicate_vendor",
                description=f"Tax ID '{tid}' shared by multiple vendor names: {raw_names}",
                impact=total_amount * 0.08,
                confidence=0.92,
                reason="Same PAN/GSTIN registered under different vendor names – strong indicator of split-billing fraud.",
                recommendation="Block duplicate tax-ID registration in ERP; escalate to compliance.",
                source_rows=idxs,
            ))

    return anomalies, groups


# ---------------------------------------------------------------------------
# B. Transaction Anomalies (duplicate payments, spikes)
# ---------------------------------------------------------------------------

def detect_transaction_anomalies(df: pd.DataFrame) -> list[dict]:
    anomalies: list[dict] = []

    amount_col = _find_col(df, "amount", "debit", "credit", "value", "spend", "cost", "total")
    date_col = _find_col(df, "date", "month", "period", "txn_date")
    vendor_col = _find_col(df, "vendor", "supplier", "name", "narration", "remarks", "description")

    if amount_col is None:
        logger.warning("transaction_anomalies: no amount column found")
        return anomalies

    amounts = _numeric_col(df, amount_col)
    vendors = _text_col(df, vendor_col)

    # --- Duplicate payments: same amount + same vendor within close period ---
    seen: dict[tuple, list[int]] = defaultdict(list)
    for idx in df.index:
        v = normalize_vendor(vendors.iloc[idx])
        a = round(float(amounts.iloc[idx]), 2)
        if a <= 0:
            continue
        key = (v, a)
        seen[key].append(int(idx))

    for (vendor, amount), idxs in seen.items():
        if len(idxs) < 2:
            continue
        if _is_recurring(amounts, amount):
            continue  # likely a subscription – false positive
        if _is_internal(vendor):
            continue

        extra_payments = len(idxs) - 1
        impact = amount * extra_payments
        confidence = min(0.65 + 0.05 * extra_payments, 0.95)
        anomalies.append(_anomaly(
            atype="duplicate_payment",
            description=f"Amount ₹{amount:,.2f} paid {len(idxs)}x to vendor '{vendor}'",
            impact=impact,
            confidence=confidence,
            reason=f"Identical amount repeated {len(idxs)} times for the same normalized vendor – possible duplicate payment.",
            recommendation="Verify each transaction has a unique invoice reference; enable ERP duplicate-payment guard.",
            source_rows=idxs,
        ))

    # --- High-frequency high-value transactions ---
    if len(amounts) > 5:
        q95 = amounts.quantile(0.95)
        high_val = df[amounts > q95]
        if not high_val.empty and len(high_val) > 3:
            total = float(amounts[amounts > q95].sum())
            anomalies.append(_anomaly(
                atype="spike",
                description=f"{len(high_val)} transactions exceed the 95th-percentile threshold of ₹{q95:,.0f}",
                impact=total * 0.02,
                confidence=0.60,
                reason="Cluster of unusually high-value transactions may indicate unauthorized spend.",
                recommendation="Require dual-approval for transactions above ₹{:,.0f}.".format(q95),
                source_rows=high_val.index.tolist(),
            ))

    return anomalies


# ---------------------------------------------------------------------------
# C. Budget Variance Analysis
# ---------------------------------------------------------------------------

def detect_budget_issues(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    anomalies: list[dict] = []
    issues: list[dict] = []

    budget_col = _find_col(df, "budget")
    actual_col = _find_col(df, "actual", "spend", "expenditure")
    dept_col = _find_col(df, "department", "cost_centre", "cost_center", "dept")

    if budget_col is None or actual_col is None:
        logger.warning("budget_issues: budget or actual column not found")
        return anomalies, issues

    budgets = _numeric_col(df, budget_col)
    actuals = _numeric_col(df, actual_col)
    depts = _text_col(df, dept_col, "Unknown")

    for idx in df.index:
        b = float(budgets.iloc[idx])
        a = float(actuals.iloc[idx])
        if b <= 0:
            continue
        var_pct = (a - b) / b * 100
        impact = max(a - b, 0.0)
        dept = str(depts.iloc[idx])

        if var_pct > 30:
            severity, confidence = "critical", 0.90
        elif var_pct > 20:
            severity, confidence = "high", 0.75
        elif var_pct > 10:
            severity, confidence = "medium", 0.55
        else:
            continue  # within acceptable range

        desc = f"{dept}: actual ₹{a:,.0f} vs budget ₹{b:,.0f} ({var_pct:+.1f}%)"
        anomalies.append(_anomaly(
            atype="budget_variance",
            description=desc,
            impact=impact,
            confidence=confidence,
            reason=f"Actual spend is {var_pct:.1f}% above budget – categorized as {severity}.",
            recommendation="Implement monthly budget gates; freeze discretionary spend until next review cycle.",
            source_rows=[int(idx)],
        ))
        issues.append({
            "department": dept,
            "budget": round(b, 2),
            "actual": round(a, 2),
            "variance_inr": round(a - b, 2),
            "variance_pct": round(var_pct, 2),
            "severity": severity,
        })

    return anomalies, issues


# ---------------------------------------------------------------------------
# D. Procurement Overpricing
# ---------------------------------------------------------------------------

def detect_overpricing(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    anomalies: list[dict] = []
    flags: list[dict] = []

    item_col = _find_col(df, "item", "description", "product", "item_description")
    price_col = _find_col(df, "unit_price", "price", "rate", "cost")
    qty_col = _find_col(df, "quantity", "qty", "units")
    bench_col = _find_col(df, "benchmark", "market_price", "standard_price")

    if item_col is None or price_col is None:
        logger.warning("overpricing: item or price column not found")
        return anomalies, flags

    try:
        from rapidfuzz import fuzz, process as rfprocess
        _fuzzy = True
    except ImportError:
        _fuzzy = False

    prices = _numeric_col(df, price_col)
    qtys = _numeric_col(df, qty_col).replace(0, 1).fillna(1)
    items = _text_col(df, item_col)

    for idx in df.index:
        item_text = str(items.iloc[idx]).strip()
        if not item_text or item_text.lower() in ("nan", "none", ""):
            continue
        unit_price = float(prices.iloc[idx])
        qty = float(qtys.iloc[idx])
        if unit_price <= 0:
            continue

        # Use explicit benchmark column if available
        benchmark: float | None = None
        if bench_col:
            benchmark = clean_numeric(df[bench_col].iloc[idx])

        # Fall back to keyword benchmarks
        if benchmark is None:
            if _fuzzy:
                match = rfprocess.extractOne(
                    item_text.lower().replace(" ", "_"),
                    BENCHMARKS.keys(),
                    scorer=fuzz.token_sort_ratio,
                )
                if match and match[1] >= 70:
                    benchmark = BENCHMARKS[match[0]]
            else:
                for key in BENCHMARKS:
                    if key.replace("_", " ") in item_text.lower():
                        benchmark = BENCHMARKS[key]
                        break

        if benchmark is None:
            continue

        threshold = 0.15  # 15% tolerance
        if unit_price <= benchmark * (1 + threshold):
            continue

        overpct = (unit_price / benchmark - 1) * 100
        overspend = (unit_price - benchmark) * qty
        confidence = min(0.6 + overpct / 200, 0.95)

        anomalies.append(_anomaly(
            atype="overpricing",
            description=f"'{item_text}' priced at ₹{unit_price:,.0f} vs benchmark ₹{benchmark:,.0f} ({overpct:.1f}% over)",
            impact=overspend,
            confidence=confidence,
            reason=f"Unit price exceeds market benchmark by {overpct:.1f}% — above the 15% acceptable threshold.",
            recommendation="Renegotiate with supplier or switch to benchmarked alternative vendor.",
            source_rows=[int(idx)],
        ))
        flags.append({
            "item": item_text,
            "unit_price": round(unit_price, 2),
            "benchmark": round(benchmark, 2),
            "overprice_pct": round(overpct, 2),
            "overspend_inr": round(overspend, 2),
            "quantity": qty,
        })

    return anomalies, flags


# ---------------------------------------------------------------------------
# E. Cloud Cost Anomalies
# ---------------------------------------------------------------------------

def detect_cloud_anomalies(df: pd.DataFrame) -> list[dict]:
    anomalies: list[dict] = []

    date_col = _find_col(df, "date", "month", "period")
    service_col = _find_col(df, "service", "resource", "instance")
    spend_col = _find_col(df, "cost", "spend", "amount", "charge")
    usage_col = _find_col(df, "usage", "utilization", "units")

    if spend_col is None:
        logger.warning("cloud_anomalies: no spend column found")
        return anomalies

    spends = _numeric_col(df, spend_col)

    # Month-over-month spike (>30% increase)
    if date_col:
        df2 = df.copy()
        df2["_spend"] = spends
        df2["_date"] = pd.to_datetime(df2[date_col], errors="coerce")
        df2 = df2.dropna(subset=["_date"]).sort_values("_date")

        iter_groups = [(None, df2)] if service_col is None else df2.groupby(service_col)
        for service, grp in iter_groups:
            grp = grp.sort_values("_date").copy()
            if len(grp) < 2:
                continue
            grp["_pct_change"] = grp["_spend"].pct_change() * 100
            spikes = grp[grp["_pct_change"] > 30]
            for i, row in spikes.iterrows():
                svc = service or "Cloud"
                pct = float(row["_pct_change"])
                s = float(row["_spend"])
                anomalies.append(_anomaly(
                    atype="cloud_spike",
                    description=f"{svc} spend jumped {pct:.1f}% in period {row['_date'].strftime('%Y-%m')}",
                    impact=s * 0.3,
                    confidence=0.75,
                    reason=f"Month-over-month increase of {pct:.1f}% exceeds the 30% threshold.",
                    recommendation="Apply auto-scaling limits and savings plans; investigate root cause in CloudWatch/GCP Billing.",
                    source_rows=[int(i)],
                ))

    # Idle resources (usage = 0, spend > 0)
    if usage_col:
        usages = pd.to_numeric(df[usage_col], errors="coerce").fillna(0)
        idle = df[(usages == 0) & (spends > 0)]
        if len(idle) >= 3:
            idle_waste = float(spends[idle.index].sum())
            anomalies.append(_anomaly(
                atype="idle_resource",
                description=f"{len(idle)} cloud resource records show zero usage but positive spend (₹{idle_waste:,.0f} total)",
                impact=idle_waste,
                confidence=0.85,
                reason="Resources billed with zero utilization for 3+ periods — indicates orphaned/idle infrastructure.",
                recommendation="Terminate or snapshot idle resources; enforce auto-shutdown policies for non-prod environments.",
                source_rows=idle.index.tolist(),
            ))

    # Rolling 30-day anomaly on aggregate spend
    if len(spends) >= 10:
        rolling_mean = spends.rolling(window=min(30, len(spends) // 2), min_periods=3).mean()
        spike_mask = spends > 2.5 * rolling_mean
        if spike_mask.any():
            total_spike = float(spends[spike_mask].sum())
            anomalies.append(_anomaly(
                atype="cloud_spike",
                description=f"{int(spike_mask.sum())} records exceed 2.5× the 30-day rolling mean spend",
                impact=total_spike * 0.4,
                confidence=0.80,
                reason="Spend exceeded 2.5× rolling average – statistically significant anomaly.",
                recommendation="Enable budget alerts and review reserved instance coverage.",
                source_rows=spike_mask[spike_mask].index.tolist(),
            ))

    return anomalies


# ---------------------------------------------------------------------------
# Public pipeline entry point
# ---------------------------------------------------------------------------

def run_analysis(grouped: dict[str, list[pd.DataFrame]]) -> dict[str, Any]:
    """
    Run all detectors on the classified DataFrames.
    Returns the full structured output.
    """
    all_anomalies: list[dict] = []
    all_duplicates: list[dict] = []
    all_overpricing: list[dict] = []
    all_budget_issues: list[dict] = []
    recommendations: set[str] = set()
    total_spend = 0.0

    def _run_on_dfs(dfs: list[pd.DataFrame], fn, *extra):
        results = []
        for df in dfs:
            if not df.empty:
                out = fn(df, *extra)
                if isinstance(out, tuple):
                    results.append(out)
                else:
                    results.append((out,))
        return results

    # Vendor tables
    for df in grouped.get("vendor", []):
        if df.empty:
            continue
        amount_col = _find_col(df, "amount", "invoice", "total", "value")
        if amount_col:
            total_spend += float(pd.to_numeric(df[amount_col], errors="coerce").fillna(0).sum())
        anoms, dups = detect_duplicate_vendors(df)
        all_anomalies.extend(anoms)
        all_duplicates.extend(dups)

    # Transaction tables
    for df in grouped.get("transaction", []):
        if df.empty:
            continue
        amount_col = _find_col(df, "amount", "debit", "credit", "value")
        if amount_col:
            total_spend += float(pd.to_numeric(df[amount_col], errors="coerce").fillna(0).sum())
        anoms = detect_transaction_anomalies(df)
        all_anomalies.extend(anoms)
        dup_anoms, dups = detect_duplicate_vendors(df)
        all_anomalies.extend(dup_anoms)
        all_duplicates.extend(dups)

    # Budget tables
    for df in grouped.get("budget", []):
        if df.empty:
            continue
        anoms, issues = detect_budget_issues(df)
        all_anomalies.extend(anoms)
        all_budget_issues.extend(issues)

    # Procurement tables
    for df in grouped.get("procurement", []):
        if df.empty:
            continue
        amount_col = _find_col(df, "unit_price", "price", "cost", "amount")
        qty_col = _find_col(df, "quantity", "qty")
        if amount_col:
            prices = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
            qtys = pd.to_numeric(df[qty_col], errors="coerce").fillna(1) if qty_col else pd.Series([1] * len(df))
            total_spend += float((prices * qtys).sum())
        anoms, flags = detect_overpricing(df)
        all_anomalies.extend(anoms)
        all_overpricing.extend(flags)

    # Cloud tables
    for df in grouped.get("cloud", []):
        if df.empty:
            continue
        spend_col = _find_col(df, "cost", "spend", "amount", "charge")
        if spend_col:
            total_spend += float(pd.to_numeric(df[spend_col], errors="coerce").fillna(0).sum())
        anoms = detect_cloud_anomalies(df)
        all_anomalies.extend(anoms)

    # Unclassified – run all detectors and pick the best fit
    for df in grouped.get("unclassified", []):
        if df.empty:
            continue
        a1, d1 = detect_duplicate_vendors(df)
        a2 = detect_transaction_anomalies(df)
        a3, i3 = detect_budget_issues(df)
        a4, f4 = detect_overpricing(df)
        a5 = detect_cloud_anomalies(df)
        all_anomalies.extend(a1 + a2 + a3 + a4 + a5)
        all_duplicates.extend(d1)
        all_budget_issues.extend(i3)
        all_overpricing.extend(f4)

    # Sort by impact desc
    all_anomalies.sort(key=lambda x: x["impact"], reverse=True)

    # Deduplicate recommendations
    for a in all_anomalies:
        recommendations.add(a["recommendation"])

    # Total savings potential
    total_savings = sum(a["impact"] for a in all_anomalies if not a.get("false_positive"))

    return {
        "total_spend": round(total_spend, 2),
        "total_savings_potential": round(total_savings, 2),
        "anomaly_count": len(all_anomalies),
        "anomalies": all_anomalies,
        "duplicate_vendors": all_duplicates,
        "overpricing_flags": all_overpricing,
        "budget_issues": all_budget_issues,
        "recommendations": sorted(recommendations),
    }
