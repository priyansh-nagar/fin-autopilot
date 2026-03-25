from typing import Any

from pydantic import BaseModel, Field


class Finding(BaseModel):
    id: str = ""
    category: str
    severity: str
    title: str
    inrImpact: int
    rootCause: str
    recommendation: str
    effort: str
    sourceRows: list[int] = Field(default_factory=list)
    detectorId: str
    isTrap: bool = False


class DetectResponse(BaseModel):
    success: bool
    totalWasteINR: int
    findingCount: int
    findings: list[Finding]
    summary: dict[str, dict[str, int]]
    scorecard: dict[str, Any]
