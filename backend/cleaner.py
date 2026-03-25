"""
cleaner.py – Data cleaning, normalisation, reshaping, and table-type detection.
"""

from __future__ import annotations

import re
import string
import logging
from typing import Literal

import pandas as pd

logger = logging.getLogger(__name__)

TableType = Literal["vendor", "cloud", "procurement", "budget", "transaction", "unclassified"]

# ---------------------------------------------------------------------------
# Column-keyword maps for classification
# ---------------------------------------------------------------------------

_TYPE_KEYWORDS: dict[TableType, list[str]] = {
    "vendor":      ["invoice", "vendor", "gstin", "pan", "supplier", "inv_id", "bill"],
    "cloud":       ["ec2", "s3", "rds", "lambda", "aws", "gcp", "azure", "cloud", "region", "instance", "cloudfront"],
    "procurement": ["po_id", "unit_price", "benchmark", "purchase", "unit price", "item description"],
    "budget":      ["budget", "actual", "variance", "department", "cost_centre", "bgt", "act"],
    "transaction": ["debit", "credit", "narration", "balance", "txn_id", "txn id"],
}

# ---------------------------------------------------------------------------
# Currency / numeric cleaning
# ---------------------------------------------------------------------------

_CURRENCY_RE = re.compile(r"[₹$€£,\s]")


def clean_numeric(value: object) -> float | None:
    if value is None or str(value).strip() in ("", "-", "—", "N/A", "na", "nan"):
        return None
    s = _CURRENCY_RE.sub("", str(value)).strip()
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Vendor name normalisation
# ---------------------------------------------------------------------------

_PUNCT_RE = re.compile(r"[%s]" % re.escape(string.punctuation))
_SUFFIXES = re.compile(
    r"\b(pvt|ltd|limited|inc|corp|technologies|technology|tech|solutions|"
    r"services|group|enterprises|india|co|llp|lp)\b",
    re.IGNORECASE,
)


def normalize_vendor(name: object) -> str:
    if not name or str(name).strip() in ("", "nan", "None"):
        return ""
    s = str(name).lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _SUFFIXES.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# Fix PDF split column headers
# ---------------------------------------------------------------------------

def _repair_split_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    pdfplumber sometimes splits column headers across adjacent cells,
    e.g. "Unit Price (IN" | "R)Benchmark (I" | "NRVa)riance".
    Detect these by checking for unclosed parentheses and remap to clean names.
    """
    raw_cols = list(df.columns)
    rename: dict[str, str] = {}

    # Known-bad pattern → clean name mapping (case-insensitive substring match)
    patterns = [
        (["unit price", "unit_price", "price/unit", "unit pri"],                   "unit_price"),
        (["benchmark", "bench mark", "r)bench", "benchmar"],                       "benchmark"),
        (["nrva", ")riance", "varianc", "variance", "var %", "var%"],              "variance_pct"),
        (["item desc", "item_desc", "description", "item"],                        "item"),
        (["po id", "po_id", "poid"],                                               "po_id"),
        (["vendor", "supplier", "vendor name"],                                    "vendor"),
        (["qty", "quantity", "units"],                                             "qty"),
        (["total (inr", "total(inr", "total inr", "total_inr", "total"],          "total_inr"),
        (["flag", "anomaly"],                                                      "flag"),
        (["category", "categ"],                                                    "category"),
        (["approved", "approval"],                                                 "approved_by"),
        (["var %", "var%", "variance %"],                                          "variance_pct"),
    ]

    for col in raw_cols:
        cl = col.lower().strip()
        for kws, target in patterns:
            if any(kw in cl for kw in kws):
                rename[col] = target
                break

    if rename:
        # Build new column list avoiding duplicates
        new_cols = []
        seen: dict[str, int] = {}
        for col in raw_cols:
            name = rename.get(col, col)
            if name in seen:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            else:
                seen[name] = 0
            new_cols.append(name)
        df = df.copy()
        df.columns = new_cols

    return df


# ---------------------------------------------------------------------------
# Normalize column names to standard lowercase_underscore
# ---------------------------------------------------------------------------

_GENERIC_COL_MAP = [
    # amount / spend
    (["amount (inr", "amount(inr", "amount_inr", "invoice amount", "inv. amount",
      "credit amount", "debit amount", "net (inr", "net(inr"], "amount"),
    # vendor
    (["credit party", "payee", "paid to", "vendor name", "supplier name"], "vendor"),
    (["debit party", "paid by", "payer"],                                  "payer"),
    # date
    (["inv. date", "invoice date", "txn date", "transaction date", "bill date"], "date"),
    # gstin / pan
    (["gstin"],                                                             "gstin"),
    (["pan"],                                                               "pan"),
    # cloud
    (["ec2 (inr", "ec2(inr", "ec2_inr"],                                   "ec2"),
    (["s3 (inr", "s3(inr", "s3_inr"],                                      "s3"),
    (["rds (inr", "rds(inr", "rds_inr"],                                   "rds"),
    (["lambda (inr", "lambda(inr", "lambda_inr"],                          "lambda"),
    (["cloudfront (inr", "cloudfront_inr"],                                "cloudfront"),
    (["network (inr", "network_inr"],                                      "network"),
    (["total (inr", "total(inr", "total_inr", "total spend"],              "total"),
    (["mom change", "mom %", "vs baseline", "mom_change"],                 "mom_change"),
    # budget
    (["q1 budget", "q1_budget", "q1 bgt", "q1_bgt"],                      "q1_budget"),
    (["q1 actual", "q1_actual", "q1 act", "q1_act"],                      "q1_actual"),
    (["q2 budget", "q2_budget", "q2 bgt", "q2_bgt"],                      "q2_budget"),
    (["q2 actual", "q2_actual", "q2 act", "q2_act"],                      "q2_actual"),
    (["q3 budget", "q3_budget", "q3 bgt", "q3_bgt"],                      "q3_budget"),
    (["q3 actual", "q3_actual", "q3 act", "q3_act"],                      "q3_actual"),
    (["q4 budget", "q4_budget", "q4 bgt", "q4_bgt"],                      "q4_budget"),
    (["q4 actual", "q4_actual", "q4 act", "q4_act", "q4 act (est"],       "q4_actual"),
    (["q1 var", "q1_var"],                                                 "q1_variance"),
    (["q2 var", "q2_var"],                                                 "q2_variance"),
    (["q3 var", "q3_var", "q3 variance"],                                  "q3_variance"),
    (["q4 var", "q4_var"],                                                 "q4_variance"),
    (["cc code", "cc_code", "cost centre", "cost_centre", "cost center"],  "cost_centre"),
    (["department", "dept"],                                               "department"),
    (["status"],                                                           "status"),
    # procurement
    (["unit price", "unit_price"],                                         "unit_price"),
    (["benchmark", "market price", "standard price"],                      "benchmark"),
    (["qty", "quantity", "units"],                                         "qty"),
    (["item description", "item_description", "item", "description"],      "item"),
    (["total (inr", "total_inr"],                                          "total_inr"),
]


def _normalize_col(col: str) -> str:
    cl = col.lower().strip()
    for patterns, target in _GENERIC_COL_MAP:
        if any(p in cl for p in patterns):
            return target
    # Generic: lowercase + underscores
    cl = re.sub(r"[\s\-/]+", "_", cl)
    cl = re.sub(r"[^a-z0-9_]", "", cl)
    cl = re.sub(r"_+", "_", cl).strip("_")
    return cl or "col"


def _apply_col_normalization(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    new_cols = []
    seen: dict[str, int] = {}
    for col in df.columns:
        name = _normalize_col(str(col))
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        new_cols.append(name)
    df.columns = new_cols
    return df


# ---------------------------------------------------------------------------
# Numeric coercion
# ---------------------------------------------------------------------------

def _coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        numeric_series = df[col].apply(clean_numeric)
        non_null = numeric_series.dropna()
        non_empty = df[col].apply(lambda x: str(x).strip() not in ("", "nan", "None"))
        if non_empty.sum() > 0 and len(non_null) / max(non_empty.sum(), 1) > 0.5:
            df[col] = numeric_series
    return df


# ---------------------------------------------------------------------------
# Budget multi-quarter reshape
# ---------------------------------------------------------------------------

def reshape_budget(df: pd.DataFrame) -> pd.DataFrame:
    """
    If a budget table has Q1_budget / Q1_actual columns, melt them into
    individual rows: {department, cost_centre, quarter, budget, actual, variance_pct}.
    This is what the frontend Budgets.tsx expects.
    """
    cols = set(df.columns)
    has_q = any(c.startswith("q") and "_budget" in c for c in cols)
    if not has_q:
        # Already row-per-quarter or single budget/actual
        return df

    dept_col = next((c for c in ["department", "dept"] if c in cols), None)
    cc_col   = next((c for c in ["cost_centre", "cc_code"] if c in cols), None)

    rows = []
    for _, row in df.iterrows():
        dept = str(row[dept_col]) if dept_col else "Unknown"
        cc   = str(row[cc_col])   if cc_col   else ""
        for q in ["q1", "q2", "q3", "q4"]:
            b_col = f"{q}_budget"
            a_col = f"{q}_actual"
            v_col = f"{q}_variance"
            if b_col not in cols and a_col not in cols:
                continue
            b = clean_numeric(row.get(b_col)) or 0.0
            a = clean_numeric(row.get(a_col)) or 0.0
            v = clean_numeric(row.get(v_col)) if v_col in cols else (
                ((a - b) / b * 100) if b else 0
            )
            rows.append({
                "department":   dept,
                "cost_centre":  cc,
                "quarter":      q.upper(),
                "budget":       b,
                "actual":       a,
                "variance_pct": round(v or 0, 2),
                "status":       str(row.get("status", "")) if "status" in cols else "",
            })

    if not rows:
        return df

    out = pd.DataFrame(rows)
    logger.info("Budget reshaped: %d source rows → %d quarter-rows", len(df), len(out))
    return out


# ---------------------------------------------------------------------------
# Cloud billing reshape
# ---------------------------------------------------------------------------

_CLOUD_SERVICE_COLS = ["ec2", "s3", "rds", "lambda", "cloudfront", "network"]


def reshape_cloud(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cloud billing tables have service names as columns (EC2, S3, RDS, …).
    Melt into rows: {month, service, cost, mom_change}.
    The frontend CloudSpend.tsx reads row.month, row.service, row.cost.
    """
    cols = set(df.columns)
    service_cols = [c for c in _CLOUD_SERVICE_COLS if c in cols]

    if not service_cols:
        # Try to detect by "total" + month
        if "total" not in cols and "month" not in cols:
            return df
        # Just alias total → cost if needed
        if "total" in cols and "cost" not in cols:
            df = df.copy()
            df["cost"] = pd.to_numeric(df["total"], errors="coerce")
        return df

    month_col = next((c for c in ["month", "date", "period"] if c in cols), None)
    mom_col   = "mom_change" if "mom_change" in cols else None

    rows = []
    for _, row in df.iterrows():
        month = str(row[month_col]) if month_col else "Unknown"
        mom   = clean_numeric(row[mom_col]) if mom_col else None
        for svc in service_cols:
            cost = clean_numeric(row.get(svc)) or 0.0
            if cost == 0:
                continue
            rows.append({
                "month":      month,
                "service":    svc.upper(),
                "cost":       cost,
                "mom_change": mom,
            })
        # Also store the total row
        if "total" in cols:
            rows.append({
                "month":      month,
                "service":    "TOTAL",
                "cost":       clean_numeric(row.get("total")) or 0.0,
                "mom_change": mom,
            })

    if not rows:
        return df

    out = pd.DataFrame(rows)
    logger.info("Cloud reshaped: %d source rows → %d service-rows", len(df), len(out))
    return out


# ---------------------------------------------------------------------------
# Table type detection
# ---------------------------------------------------------------------------

def detect_table_type(df: pd.DataFrame) -> TableType:
    col_text = " ".join(str(c).lower() for c in df.columns)
    scores: dict[str, int] = {}
    for ttype, keywords in _TYPE_KEYWORDS.items():
        scores[ttype] = sum(1 for kw in keywords if kw in col_text)
    best = max(scores, key=lambda k: scores[k])  # type: ignore
    if scores[best] == 0:
        best = "unclassified"
    logger.info("Table type detected: %s (scores=%s)", best, scores)
    return best  # type: ignore


# ---------------------------------------------------------------------------
# Full cleaning pipeline
# ---------------------------------------------------------------------------

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = _repair_split_cols(df)
    df = _apply_col_normalization(df)
    df = df.replace({"": None, "nan": None, "None": None, "N/A": None, "n/a": None})
    df = df.dropna(how="all")
    df = _coerce_numeric_columns(df)
    df = df.reset_index(drop=True)
    if df.empty:
        logger.warning("clean_dataframe: result is empty")
    return df


def classify_and_clean(dfs: list[pd.DataFrame]) -> dict[str, list[pd.DataFrame]]:
    grouped: dict[str, list[pd.DataFrame]] = {
        "vendor": [], "cloud": [], "procurement": [],
        "budget": [], "transaction": [], "unclassified": [],
    }
    for i, raw_df in enumerate(dfs):
        if raw_df is None or raw_df.empty:
            continue
        cleaned = clean_dataframe(raw_df)
        if cleaned.empty:
            continue
        ttype = detect_table_type(cleaned)
        grouped[ttype].append(cleaned)
        logger.info("DataFrame[%d] → type=%s, shape=%s", i, ttype, cleaned.shape)
    return grouped


# ---------------------------------------------------------------------------
# Normalize records for frontend consumption
# ---------------------------------------------------------------------------

def normalize_records_for_frontend(
    records: list[dict], table_type: str
) -> list[dict]:
    """
    Given a list of row dicts (from the PDF parser), normalize column names and
    values so the React frontend pages can read them with their expected field names.
    """
    if not records:
        return records

    df = pd.DataFrame(records)
    df = _repair_split_cols(df)
    df = _apply_col_normalization(df)
    df = df.replace({"": None, "nan": None, "None": None, "N/A": None, "n/a": None})
    df = df.dropna(how="all")

    if table_type == "budget":
        df = reshape_budget(df)
    elif table_type == "cloud":
        df = reshape_cloud(df)

    # Coerce numerics — use clean_numeric to handle Indian comma formatting
    TEXT_COLS = {
        "department", "vendor", "item", "month", "service", "quarter",
        "cost_centre", "status", "date", "gstin", "pan", "po_id",
        "payer", "category", "flag", "remarks", "ref_no", "approved_by",
        "mom_change", "narration", "description", "approved_by",
    }
    for col in df.columns:
        if col in TEXT_COLS:
            df[col] = df[col].fillna("").astype(str)
        else:
            # Try clean_numeric (handles commas, ₹, parentheses) then fall back to string
            numeric_series = df[col].apply(clean_numeric)
            non_null = numeric_series.notna()
            non_empty = df[col].apply(lambda x: str(x).strip() not in ("", "nan", "None", ""))
            if non_empty.sum() > 0 and non_null.sum() / max(non_empty.sum(), 1) >= 0.4:
                df[col] = numeric_series
            else:
                df[col] = df[col].fillna("").astype(str)

    df = df.reset_index(drop=True)
    return df.fillna("").to_dict(orient="records")
