from __future__ import annotations

from itertools import combinations

from rapidfuzz import fuzz

from backend.models import Finding


def run(data: dict) -> list[Finding]:
    rows = data.get("payroll", [])
    findings: list[Finding] = []

    for idx, r in enumerate(rows):
        name = str(r.get("name", r.get("employee", ""))).lower()
        emp = str(r.get("emp id", r.get("emp_id", ""))).upper()
        tds = float(r.get("tds", 0) or 0)
        gross = float(r.get("gross", r.get("salary", 0)) or 0)
        typ = str(r.get("type", "")).lower()
        if any(k in name for k in ["[deleted", "deleted user", "unknown", "n/a", "inactive"]) or "999" in emp or (typ == "contractor" and tds == 0 and gross > 0):
            findings.append(Finding(
                category="payroll", severity="critical", title=f"Ghost payroll entry detected ({emp or name})",
                inrImpact=int(gross), rootCause="Inactive/placeholder employee or contractor without TDS deduction.",
                recommendation="Block payment and run payroll master audit.", effort="1 day", sourceRows=[idx], detectorId="F_G1"
            ))

    for (i, a), (j, b) in combinations(list(enumerate(rows)), 2):
        ma, mb = str(a.get("month", "")), str(b.get("month", ""))
        da, db = str(a.get("department", "")), str(b.get("department", ""))
        if ma != mb or da != db:
            continue
        if str(a.get("type", "")).lower() == str(b.get("type", "")).lower():
            continue
        na, nb = str(a.get("name", "")), str(b.get("name", ""))
        score = max(fuzz.token_sort_ratio(na, nb), fuzz.partial_ratio(na, nb), fuzz.token_set_ratio(na, nb))
        ga, gb = float(a.get("gross", 0) or 0), float(b.get("gross", 0) or 0)
        if score >= 70 and min(ga, gb) > 0 and abs(ga - gb) / min(ga, gb) <= 0.10:
            contractor_amount = int(gb if str(b.get("type", "")).lower() == "contractor" else ga)
            findings.append(Finding(
                category="payroll", severity="critical", title=f"Dual payroll pattern: {na} vs {nb}",
                inrImpact=contractor_amount, rootCause="Employee and contractor paid similarly in same month and department.",
                recommendation="Freeze contractor payout and verify engagement records.", effort="2 days", sourceRows=[i, j], detectorId="F_G2"
            ))
    return findings
