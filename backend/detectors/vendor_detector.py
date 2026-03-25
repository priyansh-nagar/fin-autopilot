from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from statistics import mean, pstdev

from rapidfuzz import fuzz

from backend.models import Finding


def _amount(row: dict) -> float:
    for k in ["amount (inr)", "amount", "total (inr)"]:
        if k in row and row[k] not in ("", None):
            return float(row[k])
    return 0.0


def _name(row: dict) -> str:
    for k in ["vendor name", "credit party", "debit party", "vendor_name"]:
        if k in row and row[k]:
            return str(row[k]).strip()
    return ""


def run(data: dict) -> list[Finding]:
    rows = data.get("vendor", [])
    findings: list[Finding] = []

    by_pan = defaultdict(list)
    for idx, row in enumerate(rows):
        pan = str(row.get("pan", "")).strip().upper()
        by_pan[pan].append((idx, row))

    for pan, members in by_pan.items():
        if not pan:
            continue
        names = {_name(r).lower() for _, r in members if _name(r)}
        if len(names) < 2:
            continue
        total = int(sum(_amount(r) for _, r in members))
        findings.append(Finding(
            category="vendor", severity="critical",
            title=f"Vendor '{max(names, key=len).title()}' billed under {len(names)} name variants",
            inrImpact=total,
            rootCause="Same PAN appears under multiple vendor-name variants.",
            recommendation="Consolidate vendor master and block duplicate invoice routing.",
            effort="1 day", sourceRows=[i for i, _ in members], detectorId="F_V1"
        ))

    # name-only fuzzy grouping with guards
    ung = [(i, r) for i, r in enumerate(rows) if not str(r.get("pan", "")).strip()]
    for (i, a), (j, b) in combinations(ung, 2):
        na, nb = _name(a), _name(b)
        if not na or not nb or na.lower() == nb.lower():
            continue
        if any(x in na.lower() for x in ["south zone", "north zone", "east zone", "west zone", "internal", "recharge", "irc"]):
            continue
        score = fuzz.token_sort_ratio(na, nb)
        if score < 85:
            continue

        amounts = [_amount(a), _amount(b)]
        if len(amounts) >= 2 and mean(amounts) > 0 and pstdev(amounts) < 0.05 * mean(amounts):
            continue
        findings.append(Finding(
            category="vendor", severity="medium", title=f"Potential duplicate vendor names: {na} / {nb}",
            inrImpact=int(sum(amounts)), rootCause=f"Fuzzy similarity score {score:.0f} without PAN confirmation.",
            recommendation="Validate GST/PAN and merge if same legal entity.", effort="2 days", sourceRows=[i, j], detectorId="F_V2"
        ))

    return findings
