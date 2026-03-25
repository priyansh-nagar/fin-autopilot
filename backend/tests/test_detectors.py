from backend.detectors import budget_detector, cloud_detector, interco_detector, payroll_detector, procurement_detector, vendor_detector
from backend.parsers.csv_parser import parse_csv
from backend.parsers.pdf_parser import _parse_text_tables
from backend.routers.detect import _normalize_input


def test_vendor_finds_wipro_duplicates():
    rows = [
        {"vendor name": "Wipro Ltd", "pan": "ABCDE1234F", "amount": 100000},
        {"vendor name": "Wipro Limited", "pan": "ABCDE1234F", "amount": 200000},
        {"vendor name": "Wipro Infotech", "pan": "ABCDE1234F", "amount": 300000},
        {"vendor name": "Wipro Technologies", "pan": "ABCDE1234F", "amount": 120000},
        {"vendor name": "WIPRO", "pan": "ABCDE1234F", "amount": 120000},
    ]
    f = vendor_detector.run({"vendor": rows})
    assert f and f[0].inrImpact == 840000


def test_vendor_ignores_jio_subscription():
    rows = [{"vendor name": "Jio Internet", "amount": 42000} for _ in range(12)]
    assert vendor_detector.run({"vendor": rows}) == []


def test_vendor_ignores_internal_recharges():
    rows = [{"vendor name": "South Zone Recharge", "amount": 100000}, {"vendor name": "North Zone Recharge", "amount": 99000}]
    assert vendor_detector.run({"vendor": rows}) == []


def test_cloud_finds_ec2_spike():
    rows = [{"month": f"2024-{m:02d}-01", "account": "Prod", "ec2": 100000} for m in range(1, 7)]
    rows.append({"month": "2024-07-01", "account": "Prod", "ec2": 600000})
    f = cloud_detector.run({"cloud": rows, "idle": []})
    assert any(x.severity == "critical" for x in f)


def test_cloud_ignores_december_lambda():
    rows = [{"month": "2024-10-01", "account": "Prod", "service": "Lambda", "lambda": 60000},
            {"month": "2024-11-01", "account": "Prod", "service": "Lambda", "lambda": 65000},
            {"month": "2024-12-01", "account": "Prod", "service": "Lambda", "lambda": 250000}]
    assert cloud_detector.run({"cloud": rows, "idle": []}) == []


def test_cloud_detects_spike_without_account_column():
    rows = [
        {"month": "2024-08-01", "ec2 (inr)": 183900},
        {"month": "2024-09-01", "ec2 (inr)": 185200},
        {"month": "2024-10-01", "ec2 (inr)": 894600},
    ]
    findings = cloud_detector.run({"cloud": rows, "idle": []})
    assert any(f.detectorId == "F_C1" for f in findings)


def test_procurement_finds_laptop_overprice():
    rows = [{"item description": "Lenovo ThinkPad", "unit price": 94000, "qty": 8}]
    f = procurement_detector.run({"procurement": rows})
    assert f and f[0].inrImpact == 212000


def test_procurement_ignores_macbook():
    rows = [{"item description": "MacBook Pro 14", "unit price": 192000, "qty": 5}]
    assert procurement_detector.run({"procurement": rows}) == []


def test_procurement_ignores_low_variance():
    rows = [{"item description": "Monitor", "unit price": 32400, "qty": 1}]
    assert procurement_detector.run({"procurement": rows}) == []


def test_budget_finds_marketing_overspend():
    rows = [{"department": "Marketing", "budget": 2460000, "actual": 3620000}]
    f = budget_detector.run({"budget": rows})
    assert f and f[0].severity == "critical" and f[0].inrImpact == 1160000


def test_budget_ignores_it_underspend():
    rows = [{"department": "IT", "budget": 3600000, "actual": 3340000}]
    assert budget_detector.run({"budget": rows}) == []


def test_budget_detects_from_quarter_columns():
    rows = [{
        "department": "Marketing",
        "q1 budget": 1800000,
        "q1 actual": 1940000,
        "q2 budget": 2000000,
        "q2 actual": 2180000,
        "q3 budget": 2460000,
        "q3 actual": 3620000,
    }]
    findings = budget_detector.run({"budget": rows})
    assert findings and findings[0].inrImpact == 1480000


def test_payroll_finds_ghost_employee():
    rows = [{"emp id": "EMP-9999", "name": "[DELETED USER]", "tds": 0, "gross": 45000, "type": "Contractor"}]
    f = payroll_detector.run({"payroll": rows})
    assert f and f[0].severity == "critical"


def test_payroll_finds_dual_payment():
    rows = [
        {"name": "Priya Nair", "type": "Employee", "gross": 98000, "department": "Finance", "month": "2024-04"},
        {"name": "Priya N. Consulting", "type": "Contractor", "gross": 98000, "department": "Finance", "month": "2024-04"},
    ]
    f = payroll_detector.run({"payroll": rows})
    assert any(x.detectorId == "F_G2" for x in f)


def test_interco_finds_circular_flow():
    rows = [
        {"from entity": "A", "to entity": "B", "amount": 100000, "date": "2024-04-01"},
        {"from entity": "B", "to entity": "A", "amount": 110000, "date": "2024-04-20"},
    ]
    f = interco_detector.run({"interco": rows})
    assert f and f[0].severity == "critical"


def test_interco_ignores_gst_reverse_charge():
    rows = [
        {"from entity": "A", "to entity": "B", "amount": 100000, "date": "2024-04-01", "purpose": "gst reverse charge"},
        {"from entity": "B", "to entity": "A", "amount": 100000, "date": "2024-04-20", "purpose": "gst reverse charge"},
    ]
    assert interco_detector.run({"interco": rows}) == []


def test_csv_parser_normalizes_header_case_for_detectors():
    csv_bytes = (
        "Vendor Name,PAN,Amount (INR)\n"
        "Wipro Technologies Pvt Ltd,AAACW0603R,\"2,80,000\"\n"
        "WIPRO TECH LTD,AAACW0603R,\"2,80,000\"\n"
    ).encode()
    parsed = parse_csv(csv_bytes, "vendors.csv")
    findings = vendor_detector.run(parsed["data"])
    assert findings and findings[0].inrImpact == 560000


def test_pdf_text_fallback_parses_vendor_rows():
    raw_parts = ["""
    Txn ID  Date  Credit Party  GSTIN  PAN  Amount (INR)  Inv. Date
    TXN-001  03-Apr-24  Wipro Technologies Pvt Ltd  29AAACW0603R1ZX  AAACW0603R  2,80,000  05-Apr-2024
    TXN-002  05-Apr-24  WIPRO TECH LTD  29AAACW0603R1ZX  AAACW0603R  2,80,000  02-May-2024
    ANOMALY FLAG: sample
    """]
    parsed = _parse_text_tables(raw_parts)
    findings = vendor_detector.run(parsed)
    assert findings and findings[0].inrImpact == 560000


def test_detect_normalizes_unclassified_rows():
    payload = {
        "unclassified": [
            {"vendor name": "Wipro Ltd", "pan": "ABCDE1234F", "amount (inr)": 280000},
            {"vendor name": "WIPRO TECH LTD", "pan": "ABCDE1234F", "amount (inr)": 280000},
        ]
    }
    normalized = _normalize_input(payload)
    findings = vendor_detector.run(normalized)
    assert len(normalized["vendor"]) == 2
    assert findings and findings[0].inrImpact == 560000


def test_detect_recovers_when_header_row_is_in_data():
    payload = {
        "unclassified": [
            {"col_0": "Vendor Name", "col_1": "PAN", "col_2": "Amount (INR)"},
            {"col_0": "Wipro Ltd", "col_1": "ABCDE1234F", "col_2": "2,80,000"},
            {"col_0": "WIPRO TECH LTD", "col_1": "ABCDE1234F", "col_2": "2,80,000"},
        ]
    }
    normalized = _normalize_input(payload)
    findings = vendor_detector.run(normalized)
    assert len(normalized["vendor"]) == 2
    assert findings and findings[0].inrImpact == 560000
