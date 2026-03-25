from __future__ import annotations

from rapidfuzz import fuzz, process

from backend.models import Finding

BENCHMARKS = {
    "laptop": 67500, "thinkpad": 67500, "macbook": 188000,
    "desktop": 45000, "monitor": 28500, "server": 280000,
    "printer": 44500, "ups": 21000, "keyboard": 7200,
    "chair": 16200, "paper": 285, "paper_ream": 285,
    "toner": 2850, "cartridge": 2850,
    "zoom": 10800, "slack": 6250, "salesforce": 98500,
    "crm": 98500, "aws_reserved": 154000,
    "diesel": 94, "fuel": 94,
    "water": 72, "cctv": 11200, "shelving": 13500,
    "adobe": 58000, "creative_cloud": 58000,
}


def run(data: dict) -> list[Finding]:
    rows = data.get("procurement", [])
    findings: list[Finding] = []
    for idx, row in enumerate(rows):
        desc = str(row.get("item description", row.get("item", row.get("item_description", "")))).lower().strip()
        if not desc:
            continue
        price = float(row.get("unit price", row.get("unit_price", 0)) or 0)
        qty = float(row.get("quantity", row.get("qty", 1)) or 1)
        if "macbook" in desc or "apple" in desc:
            key, score = "macbook", 100
        else:
            m = process.extractOne(desc, BENCHMARKS.keys(), scorer=fuzz.partial_ratio, score_cutoff=65)
            if not m:
                continue
            key, score, _ = m
        benchmark = BENCHMARKS[key]
        variance_pct = ((price - benchmark) / benchmark) * 100 if benchmark else 0
        if variance_pct <= 15:
            continue
        impact = int((price - benchmark) * qty)
        severity = "critical" if variance_pct > 30 else "high" if variance_pct > 20 else "medium"
        findings.append(Finding(
            category="procurement", severity=severity,
            title=f"{desc.title()} priced {variance_pct:.0f}% above benchmark",
            inrImpact=impact,
            rootCause=f"Matched benchmark '{key}' at score {score}.",
            recommendation="Renegotiate vendor rate card and enforce benchmark approvals.",
            effort="2 days", sourceRows=[idx], detectorId="F_P1"
        ))
    return findings
