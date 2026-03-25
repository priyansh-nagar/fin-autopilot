from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from backend.models import Finding


def _parse_date(value: str) -> datetime | None:
    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def run(data: dict) -> list[Finding]:
    rows = data.get("interco", [])
    findings: list[Finding] = []
    edges = []
    for idx, r in enumerate(rows):
        purpose = str(r.get("remarks", r.get("purpose", ""))).lower()
        if any(k in purpose for k in ["repayment", "loan repayment", "emi", "gst reverse charge", "reverse charge"]):
            continue
        f = str(r.get("from entity", r.get("from", "")))
        t = str(r.get("to entity", r.get("to", "")))
        amt = float(r.get("amount", 0) or 0)
        dt = _parse_date(str(r.get("date", "")) or "")
        edges.append((idx, f, t, amt, dt))

    by_pair = defaultdict(list)
    for e in edges:
        by_pair[(e[1], e[2])].append(e)

    for (a, b), ab_list in by_pair.items():
        ba_list = by_pair.get((b, a), [])
        if not ba_list:
            continue
        for e1 in ab_list:
            for e2 in ba_list:
                amts = [e1[3], e2[3]]
                if min(amts) <= 0 or abs(e1[3] - e2[3]) / max(amts) > 0.20:
                    continue
                days = 999
                if e1[4] and e2[4]:
                    days = abs((e2[4] - e1[4]).days)
                sev = "critical" if days <= 30 else "high"
                findings.append(Finding(
                    category="interco", severity=sev, title=f"Circular inter-company flow detected: {a} ↔ {b}",
                    inrImpact=int(max(amts)), rootCause="Bidirectional inter-company transfers with near-matching amounts.",
                    recommendation="Review inter-company policy and settlement controls.", effort="1 sprint",
                    sourceRows=[e1[0], e2[0]], detectorId="F_I1"
                ))
                return findings
    return findings
