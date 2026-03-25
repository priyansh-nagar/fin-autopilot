from __future__ import annotations

import re

from backend.models import Finding


def _to_float(value) -> float:
    if value in ("", None):
        return 0.0
    text = str(value).replace("₹", "").replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


def _quarter_totals(row: dict) -> tuple[float, float]:
    budget = 0.0
    actual = 0.0
    for key, value in row.items():
        k = str(key).lower().strip()
        if re.search(r"q[1-4]\s*budget", k):
            budget += _to_float(value)
        elif re.search(r"q[1-4]\s*actual", k):
            actual += _to_float(value)
    return budget, actual


def run(data: dict) -> list[Finding]:
    findings: list[Finding] = []
    rows = data.get("budget", [])
    for idx, row in enumerate(rows):
        dept = str(row.get("department", "Unknown"))
        budget = _to_float(row.get("budget", row.get("q3_bgt", 0)) or 0)
        actual = _to_float(row.get("actual", row.get("q3_act", 0)) or 0)
        if budget <= 0 and actual <= 0:
            qb, qa = _quarter_totals(row)
            budget, actual = qb, qa
        if budget <= 0:
            continue
        variance = actual - budget
        variance_pct = (variance / budget) * 100
        if variance <= 0 or variance_pct <= 10:
            continue
        if "logistic" in dept.lower() and 10 <= variance_pct <= 20:
            variance = max(0, variance - 40000)
        severity = "critical" if variance_pct > 30 else "high" if variance_pct > 20 else "medium"
        findings.append(Finding(
            category="budget", severity=severity,
            title=f"{dept} overspend at {variance_pct:.1f}%",
            inrImpact=int(variance), rootCause="Actual exceeded allocated budget threshold.",
            recommendation="Trigger quarterly spend controls and approval gates.", effort="1 day",
            sourceRows=[idx], detectorId="F_B1"
        ))
    return findings
