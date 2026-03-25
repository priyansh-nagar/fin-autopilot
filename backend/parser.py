"""
parser.py – PDF and CSV extraction pipeline.
Primary: pdfplumber (table-aware).
Fallback: PyMuPDF (fitz) for text + regex parsing.
"""

from __future__ import annotations

import io
import logging
import re
import tempfile
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_header(h: Any) -> str:
    return str(h).strip().replace("\n", " ") if h is not None else ""


def _df_from_raw_table(raw: list[list[Any]]) -> pd.DataFrame | None:
    """Convert a raw pdfplumber table (list of lists) to a DataFrame."""
    if not raw or len(raw) < 2:
        return None
    headers = [_clean_header(c) for c in raw[0]]
    rows = []
    for row in raw[1:]:
        if row and any(cell for cell in row):
            rows.append({headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))})
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df.columns = [str(c).strip() for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# pdfplumber parser (primary)
# ---------------------------------------------------------------------------

def _parse_with_pdfplumber(content: bytes) -> tuple[list[pd.DataFrame], str]:
    """Extract tables and raw text from all pages using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not available")
        return [], ""

    dfs: list[pd.DataFrame] = []
    text_parts: list[str] = []

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        with pdfplumber.open(tmp_path) as pdf:
            logger.info("pdfplumber: %d pages found", len(pdf.pages))
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text)

                tables = page.extract_tables() or []
                logger.info("  Page %d: %d table(s) found", page_num, len(tables))

                for tbl in tables:
                    df = _df_from_raw_table(tbl)
                    if df is not None and not df.empty:
                        logger.info("    Table shape: %s, cols: %s", df.shape, list(df.columns))
                        dfs.append(df)
    except Exception as exc:
        logger.error("pdfplumber failed: %s", exc)

    return dfs, "\n".join(text_parts)


# ---------------------------------------------------------------------------
# PyMuPDF parser (fallback)
# ---------------------------------------------------------------------------

def _parse_with_fitz(content: bytes) -> tuple[list[pd.DataFrame], str]:
    """Extract text from all pages with PyMuPDF and attempt regex table parsing."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF (fitz) not available")
        return [], ""

    text_parts: list[str] = []
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        logger.info("fitz: %d pages found", len(doc))
        for page in doc:
            text_parts.append(page.get_text())
    except Exception as exc:
        logger.error("fitz failed: %s", exc)
        return [], ""

    raw_text = "\n".join(text_parts)
    dfs = _regex_parse(raw_text)
    return dfs, raw_text


# ---------------------------------------------------------------------------
# Regex-based table reconstruction from raw text
# ---------------------------------------------------------------------------

_NUMERIC = re.compile(r"^[\d,.\-₹$]+$")


def _regex_parse(text: str) -> list[pd.DataFrame]:
    """Heuristic: find lines that look like data rows and build a DataFrame."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return []

    # Find candidate header line: longest line with multiple word-chunks separated by 2+ spaces
    header_line: str | None = None
    header_idx = 0
    for i, line in enumerate(lines):
        parts = re.split(r"\s{2,}", line)
        if len(parts) >= 3:
            header_line = line
            header_idx = i
            break

    if header_line is None:
        logger.warning("regex_parse: no header candidate found, building single-column frame")
        return [pd.DataFrame({"raw_text": lines})]

    headers = [p.strip() for p in re.split(r"\s{2,}", header_line) if p.strip()]
    n_cols = len(headers)

    rows: list[dict[str, str]] = []
    for line in lines[header_idx + 1 :]:
        parts = re.split(r"\s{2,}", line)
        if len(parts) < max(2, n_cols - 2):
            continue
        # Pad / trim to header length
        while len(parts) < n_cols:
            parts.append("")
        row_dict = {headers[j]: parts[j].strip() for j in range(n_cols)}
        rows.append(row_dict)

    if not rows:
        return [pd.DataFrame({"raw_text": lines})]

    df = pd.DataFrame(rows)
    logger.info("regex_parse produced DataFrame shape %s", df.shape)
    return [df]


# ---------------------------------------------------------------------------
# CSV parser
# ---------------------------------------------------------------------------

def parse_csv(content: bytes) -> tuple[list[pd.DataFrame], str]:
    """Parse a CSV file into a list containing one DataFrame."""
    try:
        df = pd.read_csv(io.BytesIO(content))
        df.columns = [str(c).strip() for c in df.columns]
        logger.info("CSV parsed: %s", df.shape)
        return [df], ""
    except Exception as exc:
        logger.error("CSV parse failed: %s", exc)
        return [], str(exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_file(content: bytes, filename: str) -> dict[str, Any]:
    """
    Parse a PDF or CSV file.

    Returns:
        {
            "dataframes": list[pd.DataFrame],
            "raw_text": str,
            "parser_used": str,
            "page_count": int,
            "debug_log": list[str],
        }
    """
    debug: list[str] = []
    fn = filename.lower()

    if fn.endswith(".csv"):
        dfs, raw = parse_csv(content)
        debug.append(f"CSV parser: {len(dfs)} dataframe(s)")
        return {
            "dataframes": dfs,
            "raw_text": raw,
            "parser_used": "csv",
            "page_count": 0,
            "debug_log": debug,
        }

    if not fn.endswith(".pdf"):
        return {
            "dataframes": [],
            "raw_text": "",
            "parser_used": "none",
            "page_count": 0,
            "debug_log": ["Unsupported file type"],
        }

    # --- PDF: try pdfplumber first ---
    dfs, raw_text = _parse_with_pdfplumber(content)
    parser_used = "pdfplumber"

    if not dfs:
        debug.append("pdfplumber found no tables – falling back to PyMuPDF")
        dfs, raw_text = _parse_with_fitz(content)
        parser_used = "fitz+regex"

    if not dfs and raw_text:
        debug.append("fitz found no structured tables – applying regex parser")
        dfs = _regex_parse(raw_text)
        parser_used = "regex"

    for i, df in enumerate(dfs):
        debug.append(f"DataFrame[{i}] shape={df.shape}, cols={list(df.columns)}")
        if df.empty:
            debug.append(f"  !! DataFrame[{i}] is EMPTY")

    if not dfs:
        debug.append("CRITICAL: No data could be extracted from the PDF")

    return {
        "dataframes": dfs,
        "raw_text": raw_text,
        "parser_used": parser_used,
        "page_count": 0,
        "debug_log": debug,
    }
