"""
cleaner.py – Data cleaning, normalisation, and table-type detection.
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
    "vendor":       ["invoice", "vendor", "gstin", "pan", "supplier", "inv_id", "bill"],
    "cloud":        ["service", "ec2", "s3", "rds", "lambda", "aws", "gcp", "azure", "cloud", "region", "instance"],
    "procurement":  ["po_id", "unit_price", "benchmark", "purchase", "item", "description", "rate", "qty", "quantity"],
    "budget":       ["budget", "actual", "variance", "department", "cost_centre", "cost_center"],
    "transaction":  ["date", "transaction", "debit", "credit", "balance", "narration", "remarks"],
}

# ---------------------------------------------------------------------------
# Currency / numeric cleaning
# ---------------------------------------------------------------------------

_CURRENCY_RE = re.compile(r"[₹$€£,\s]")


def clean_numeric(value: object) -> float | None:
    """Strip currency symbols and commas, return float or None."""
    if value is None or str(value).strip() in ("", "-", "—", "N/A", "na", "nan"):
        return None
    s = _CURRENCY_RE.sub("", str(value)).strip()
    # Handle parentheses as negative: (1234) → -1234
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return None


def _coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Try to coerce every column to numeric where possible."""
    df = df.copy()
    for col in df.columns:
        numeric_series = df[col].apply(clean_numeric)
        non_null = numeric_series.dropna()
        # Only coerce if >50% of non-empty values parsed successfully
        non_empty = df[col].apply(lambda x: str(x).strip() not in ("", "nan", "None"))
        if non_empty.sum() > 0 and len(non_null) / max(non_empty.sum(), 1) > 0.5:
            df[col] = numeric_series
    return df


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
    """
    Normalise a vendor name for fuzzy deduplication.
    E.g. "WIPRO TECH LTD.", "Wipro Technologies" → "wipro"
    """
    if not name or str(name).strip() in ("", "nan", "None"):
        return ""
    s = str(name).lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _SUFFIXES.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# Table type detection
# ---------------------------------------------------------------------------

def detect_table_type(df: pd.DataFrame) -> TableType:
    """Classify the DataFrame into a known financial table type."""
    cols_lower = [str(c).lower().replace(" ", "_") for c in df.columns]
    col_text = " ".join(cols_lower)

    scores: dict[TableType, int] = {}
    for ttype, keywords in _TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in col_text)
        scores[ttype] = score

    best: TableType = max(scores, key=lambda k: scores[k])  # type: ignore[arg-type]
    if scores[best] == 0:
        best = "unclassified"

    logger.info("Table type detected: %s (scores=%s)", best, scores)
    return best


# ---------------------------------------------------------------------------
# Full cleaning pipeline
# ---------------------------------------------------------------------------

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise column names, coerce numerics, drop fully-empty rows."""
    df = df.copy()

    # Normalise column names
    df.columns = [
        str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns
    ]

    # Drop rows where all cells are empty/NaN
    df = df.replace({"": None, "nan": None, "None": None, "N/A": None, "n/a": None})
    df = df.dropna(how="all")

    # Coerce numerics
    df = _coerce_numeric_columns(df)

    # Reset index
    df = df.reset_index(drop=True)

    if df.empty:
        logger.warning("clean_dataframe: result is empty after cleaning")

    return df


def classify_and_clean(dfs: list[pd.DataFrame]) -> dict[str, list[pd.DataFrame]]:
    """
    Clean each DataFrame and group by detected table type.
    Returns a dict keyed by TableType with lists of cleaned DataFrames.
    """
    grouped: dict[str, list[pd.DataFrame]] = {
        "vendor": [], "cloud": [], "procurement": [],
        "budget": [], "transaction": [], "unclassified": [],
    }

    for i, raw_df in enumerate(dfs):
        if raw_df is None or raw_df.empty:
            logger.warning("Skipping empty DataFrame at index %d", i)
            continue
        cleaned = clean_dataframe(raw_df)
        if cleaned.empty:
            logger.warning("DataFrame[%d] empty after cleaning", i)
            continue
        ttype = detect_table_type(cleaned)
        grouped[ttype].append(cleaned)
        logger.info("DataFrame[%d] → type=%s, shape=%s", i, ttype, cleaned.shape)

    return grouped
