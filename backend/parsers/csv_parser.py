from __future__ import annotations

import io
from typing import Any

import pandas as pd

from .pdf_parser import classify_headers, clean_header, coerce_cell

CATEGORIES = ["vendor", "cloud", "idle", "procurement", "payroll", "budget", "interco", "unclassified"]


def parse_csv(content: bytes, file_name: str) -> dict[str, Any]:
    df = pd.read_csv(io.BytesIO(content))
    normalized_headers = [clean_header(c, i) for i, c in enumerate(df.columns)]
    df.columns = normalized_headers
    headers = [str(c) for c in df.columns]
    category = classify_headers(headers)
    rows = [
        {str(k): coerce_cell(v, str(k)) for k, v in row.items()}
        for row in df.fillna("").to_dict(orient="records")
    ]

    data = {k: [] for k in CATEGORIES}
    data[category] = rows

    row_counts = {k: len(v) for k, v in data.items()}
    return {
        "success": True,
        "fileName": file_name,
        "totalRows": sum(row_counts.values()),
        "rowCounts": row_counts,
        "data": data,
        "rawText": "",
        "pageCount": 0,
        "tablesFound": 1 if rows else 0,
    }
