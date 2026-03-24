from models import Finding
import uuid

DEMO_FINDINGS = [
    Finding(
        id=str(uuid.uuid4()),
        category="Vendor",
        severity="High",
        title='Duplicate Vendor: "wipro technologies" vs "WIPRO TECH LTD"',
        impact_inr=840000,
        root_cause="Fuzzy name matching >85% similarity with overlapping dates.",
        recommended_action="Merge vendor IDs and initiate recovery for duplicate invoices.",
        remediation_hours=2.5,
        owner="AP Team"
    ),
    Finding(
        id=str(uuid.uuid4()),
        category="Vendor",
        severity="Medium",
        title="3 GST numbers mapping to same PAN",
        impact_inr=410000,
        root_cause="Shared PAN across multiple vendor records indicating fragmented spend.",
        recommended_action="Consolidate supplier contracts for volume discount.",
        remediation_hours=4.0,
        owner="Procurement"
    ),
    Finding(
        id=str(uuid.uuid4()),
        category="Cloud",
        severity="Critical",
        title="AWS EC2 spike Oct 15–22",
        impact_inr=620000,
        root_cause="Load test environment left running on r5.8xlarge instances.",
        recommended_action="Terminate idle instances immediately.",
        remediation_hours=0.5,
        owner="DevOps"
    ),
    Finding(
        id=str(uuid.uuid4()),
        category="Cloud",
        severity="Low",
        title="14 idle S3 buckets not accessed in 90+ days",
        impact_inr=180000,
        root_cause="Unused storage resources lacking retention policies.",
        recommended_action="Archive to Glacier or delete buckets.",
        remediation_hours=1.0,
        owner="Cloud Admin"
    ),
    Finding(
        id=str(uuid.uuid4()),
        category="Procurement",
        severity="High",
        title="Lenovo laptops at ₹94,000/unit (Benchmark: ₹67,500)",
        impact_inr=1320000,
        root_cause="Unit price paid > benchmark by 39%.",
        recommended_action="Renegotiate hardware contract with OEM directly.",
        remediation_hours=8.0,
        owner="IT Procurement"
    ),
    Finding(
        id=str(uuid.uuid4()),
        category="Budget",
        severity="Critical",
        title="Marketing dept 47% over Q3 budget",
        impact_inr=1160000,
        root_cause="Unexplained variance in 'Digital Ads' cost center.",
        recommended_action="Freeze discretionary ad spend until reconciliation.",
        remediation_hours=12.0,
        owner="FP&A Lead"
    )
]
