from __future__ import annotations

from fastapi import APIRouter

from backend.detectors import budget_detector, cloud_detector, interco_detector, payroll_detector, procurement_detector, vendor_detector
from backend.models import DetectResponse, Finding
from backend.parsers.pdf_parser import classify_headers

router = APIRouter(prefix="/api", tags=["detect"])


def _assign_ids(findings: list[Finding]) -> list[Finding]:
    sorted_findings = sorted(findings, key=lambda x: x.inrImpact, reverse=True)
    for i, f in enumerate(sorted_findings, 1):
        f.id = f"F{str(i).zfill(3)}"
    return sorted_findings


def _normalize_input(payload: dict) -> dict:
    parsed = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    categories = ["vendor", "cloud", "idle", "procurement", "payroll", "budget", "interco", "unclassified"]
    data = {k: list(parsed.get(k, [])) for k in categories}

    migrated: list[dict] = []
    for row in data.get("unclassified", []):
        if not isinstance(row, dict):
            continue
        detected = classify_headers([str(k).lower() for k in row.keys()])
        if detected != "unclassified":
            data[detected].append(row)
            migrated.append(row)
    if migrated:
        data["unclassified"] = [r for r in data["unclassified"] if r not in migrated]
    return data


@router.post("/detect", response_model=DetectResponse)
async def detect(parsed_data: dict):
    parsed_data = _normalize_input(parsed_data)
    all_findings: list[Finding] = []
    all_findings += vendor_detector.run(parsed_data)
    all_findings += cloud_detector.run(parsed_data)
    all_findings += procurement_detector.run(parsed_data)
    all_findings += budget_detector.run(parsed_data)
    all_findings += payroll_detector.run(parsed_data)
    all_findings += interco_detector.run(parsed_data)

    all_findings = _assign_ids(all_findings)

    summary: dict[str, dict[str, int]] = {}
    for f in all_findings:
        summary.setdefault(f.category, {"count": 0, "totalINR": 0})
        summary[f.category]["count"] += 1
        summary[f.category]["totalINR"] += int(f.inrImpact)

    return DetectResponse(
        success=True,
        totalWasteINR=sum(int(f.inrImpact) for f in all_findings),
        findingCount=len(all_findings),
        findings=all_findings,
        summary=summary,
        scorecard={
            "anomaliesCaught": len([f for f in all_findings if not f.isTrap]),
            "targetAnomalies": 14,
            "score": f"{(len(all_findings) / 14) * 100:.0f}%",
        },
    )


@router.get("/score")
def score(findings: list[Finding]):
    caught = len([f for f in findings if not f.isTrap])
    false_positives = len([f for f in findings if f.isTrap])
    score_pct = max(0, (caught / 14) * 100 - (false_positives * 10))
    return {
        "anomaliesCaught": caught,
        "targetTotal": 14,
        "falsePositives": false_positives,
        "score": f"{score_pct:.0f}%",
        "rating": "Production ready" if score_pct >= 85 else "Hackathon ready" if score_pct >= 70 else "Needs improvement",
    }
