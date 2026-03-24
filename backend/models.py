from pydantic import BaseModel
from typing import List, Optional

class Finding(BaseModel):
    id: str
    category: str  # Vendor, Cloud, Procurement, Budget
    severity: str  # Critical, High, Medium
    title: str
    impact_inr: float
    root_cause: str
    recommended_action: str
    remediation_hours: float
    owner: str
    resolved: bool = False

class DashboardSummary(BaseModel):
    total_waste: float
    findings_count: int
    savings_recoverable: float
    data_quality_score: int

class ChatRequest(BaseModel):
    message: str
    findings_context: Optional[List[Finding]] = None

class ChatResponse(BaseModel):
    response: str
