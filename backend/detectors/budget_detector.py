from __future__ import annotations

from backend.models import Finding


def run(data: dict) -> list[Finding]:
    findings: list[Finding] = []
    rows = data.get("budget", [])
    for idx, row in enumerate(rows):
        dept = str(row.get("department", "Unknown"))
        budget = float(row.get("budget", row.get("q3_bgt", 0)) or 0)
        actual = float(row.get("actual", row.get("q3_act", 0)) or 0)
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
