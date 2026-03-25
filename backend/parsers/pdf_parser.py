from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any

import pdfplumber

CATEGORIES = ["vendor", "cloud", "idle", "procurement", "payroll", "budget", "interco", "unclassified"]

HEADER_RULES = {
    "vendor": ["txn id", "inv id", "invoice_id", "vendor name", "gstin", "pan", "debit party", "credit party", "amount", "inv. id"],
    "cloud": ["ec2", "s3", "rds", "lambda", "cloudfront", "aws", "gcp", "service", "cloud", "month", "account", "resource id"],
    "idle": ["idle", "resource id", "last used", "last accessed", "days idle", "bucket name", "monthly cost"],
    "procurement": ["po id", "unit price", "benchmark", "item description", "category", "approved by", "variance", "po_id"],
    "payroll": ["emp id", "emp/", "salary", "gross", "tds", "net", "payroll", "contractor", "bank acct"],
    "budget": ["department", "budget", "actual", "variance", "cc code", "cost centre", "q1", "q2", "q3", "q4", "status"],
    "interco": ["from entity", "to entity", "inter.company", "ic-", "circular", "related party", "recharge"],
}


DATE_FORMATS = ["%d-%b-%y", "%d-%m-%Y", "%d/%m/%Y", "%b-%y", "%b-%Y", "%d %b %Y"]

TEXT_STOP_MARKERS = ("anomaly flag", "savings summary", "note:")


def clean_header(value: Any, idx: int) -> str:
    text = str(value).strip().lower().replace("\n", " ") if value is not None else ""
    return text if text else f"col_{idx}"


def classify_headers(headers: list[str]) -> str:
    lowered = [h.lower() for h in headers]
    scores: dict[str, int] = {}
    for cat, keys in HEADER_RULES.items():
        scores[cat] = sum(1 for h in lowered for key in keys if key in h)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unclassified"


def _to_money(text: str) -> float | None:
    cleaned = text.replace("₹", "").replace(",", "").strip()
    if re.fullmatch(r"-?\d+(\.\d+)?", cleaned):
        return float(cleaned)
    return None


def _to_iso_date(text: str) -> str | None:
    raw = text.strip()
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            if fmt in {"%b-%y", "%b-%Y"}:
                dt = dt.replace(day=1)
            return dt.date().isoformat()
        except ValueError:
            continue
    m = re.fullmatch(r"([A-Za-z]{3})-(\d{2})", raw)
    if m:
        return datetime.strptime(raw, "%b-%y").date().isoformat()
    return None


def coerce_cell(value: Any, key: str) -> Any:
    text = str(value).replace("\n", " ").strip() if value is not None else ""
    if text == "":
        return ""
    money = _to_money(text)
    if money is not None and any(tok in key.lower() for tok in ["amount", "cost", "price", "budget", "actual", "gross", "net", "tds"]):
        return money
    date = _to_iso_date(text)
    if date is not None and any(tok in key.lower() for tok in ["date", "month", "used", "accessed"]):
        return date
    return text


def parse_pdf(content: bytes, file_name: str) -> dict[str, Any]:
    data = {k: [] for k in CATEGORIES}
    raw_text_parts: list[str] = []
    tables_found = 0

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text:
                raw_text_parts.append(page_text)

            strict = page.extract_tables(
                table_settings={
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict",
                    "snap_tolerance": 4,
                    "join_tolerance": 4,
                    "edge_min_length": 10,
                }
            )
            tables = strict or page.extract_tables(
                table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 4,
                    "join_tolerance": 4,
                    "edge_min_length": 10,
                }
            )

            for table in tables or []:
                if not table or len(table) < 2:
                    continue
                if len(table[0]) < 2:
                    continue

                headers = [clean_header(h, i) for i, h in enumerate(table[0])]
                rows: list[dict[str, Any]] = []
                for ridx, row in enumerate(table[1:]):
                    if not row or len(row) < 2 or not any((c or "").strip() for c in row if isinstance(c, str) or c is not None):
                        continue
                    row_dict = {headers[i]: coerce_cell(row[i] if i < len(row) else "", headers[i]) for i in range(len(headers))}
                    row_dict["_source_row"] = ridx
                    rows.append(row_dict)

                if not rows:
                    continue
                tables_found += 1
                category = classify_headers(headers)
                data[category].extend(rows)

    if tables_found == 0 and raw_text_parts:
        fallback_tables = _parse_text_tables(raw_text_parts)
        for category, rows in fallback_tables.items():
            data[category].extend(rows)
            if rows:
                tables_found += 1

    row_counts = {k: len(v) for k, v in data.items()}
    return {
        "success": True,
        "fileName": file_name,
        "totalRows": sum(row_counts.values()),
        "rowCounts": row_counts,
        "data": data,
        "rawText": "\n".join(raw_text_parts),
        "pageCount": len(raw_text_parts),
        "tablesFound": tables_found,
    }


def _parse_text_tables(raw_text_parts: list[str]) -> dict[str, list[dict[str, Any]]]:
    out = {k: [] for k in CATEGORIES}
    for text in raw_text_parts:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        active_headers: list[str] | None = None
        active_category = "unclassified"
        for line in lines:
            lower = line.lower()
            if any(marker in lower for marker in TEXT_STOP_MARKERS):
                active_headers = None
                continue

            maybe_headers = [clean_header(x, i) for i, x in enumerate(re.split(r"\s{2,}", line)) if x.strip()]
            if len(maybe_headers) >= 3:
                detected = classify_headers(maybe_headers)
                if detected != "unclassified":
                    active_headers = maybe_headers
                    active_category = detected
                    continue

            if not active_headers:
                continue

            cells = [x.strip() for x in re.split(r"\s{2,}", line) if x.strip()]
            if len(cells) < max(3, len(active_headers) - 2):
                continue
            if len(cells) > len(active_headers):
                cells = cells[: len(active_headers) - 1] + [" ".join(cells[len(active_headers) - 1 :])]

            row: dict[str, Any] = {}
            for i, key in enumerate(active_headers):
                val = cells[i] if i < len(cells) else ""
                row[key] = coerce_cell(val, key)
            if any(v not in ("", None) for v in row.values()):
                out[active_category].append(row)
    return out
