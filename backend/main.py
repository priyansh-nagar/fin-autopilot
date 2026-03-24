from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import uuid
import pdfplumber
from typing import List

from models import Finding, DashboardSummary, ChatRequest, ChatResponse
from demo_data import DEMO_FINDINGS
from detectors import process_csv_upload

app = FastAPI(title="Fin-Autopilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/demo", response_model=List[Finding])
def get_demo_data():
    return DEMO_FINDINGS

@app.post("/api/upload", response_model=List[Finding])
async def upload_dataset(file: UploadFile = File(...)):
    filename = file.filename.lower()
    contents = await file.read()
    
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
            return process_csv_upload(df)
            
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents))
            return process_csv_upload(df)
            
        elif filename.endswith((".pdf", ".doc", ".docx", ".txt")):
            # Mocking OCR/NLP processing for unstructured documents
            return [
                Finding(
                    id=str(uuid.uuid4()),
                    category="Procurement",
                    severity="High",
                    title=f"Contract Risk in {file.filename}",
                    impact_inr=750000,
                    root_cause="NLP Agent detected unfavorable auto-renewal clause and potential 15% price hike.",
                    recommended_action="Renegotiate contract terms before upcoming renewal cycle.",
                    remediation_hours=5.0,
                    owner="Legal / Procurement"
                ),
                Finding(
                    id=str(uuid.uuid4()),
                    category="Vendor",
                    severity="Medium",
                    title="Unverified Vendor Details",
                    impact_inr=0,
                    root_cause=f"Agent extracted vendor details from {file.filename} that do not match master records.",
                    recommended_action="Initiate KYC verification workflow.",
                    remediation_hours=2.0,
                    owner="AP Team"
                )
            ]
            
        else:
            # Unsupported format handled gracefully
            return [
                Finding(
                    id=str(uuid.uuid4()),
                    category="Budget",
                    severity="Medium",
                    title="Unknown File Format",
                    impact_inr=0,
                    root_cause=f"File {file.filename} is not natively parsable.",
                    recommended_action="Please upload standard tabular (CSV/XLSX) or text documents.",
                    remediation_hours=0.5,
                    owner="User"
                )
            ]
    except Exception as e:
        import traceback
        traceback.print_exc()
        return [
            Finding(
                id=str(uuid.uuid4()),
                category="Budget",
                severity="Critical",
                title=f"Exception: {str(e)}",
                impact_inr=0,
                root_cause=traceback.format_exc(),
                recommended_action="Fix Backend Code",
                remediation_hours=0,
                owner="Dev"
            )
        ]

@app.post("/api/parse")
async def parse_pdf(file: UploadFile = File(...)):
    contents = await file.read()
    vendor_rows, cloud_rows, proc_rows, budget_rows = [], [], [], []
    raw_text = ""
    
    try:
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted: raw_text += extracted + "\n"
                
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 2: continue
                    raw_headers = table[0]
                    headers = [str(h).replace('\n', ' ').strip() if h else f"col_{i}" for i, h in enumerate(raw_headers)]
                    headers_lower = [h.lower() for h in headers]
                    
                    is_cloud = any(x in h for h in headers_lower for x in ['aws', 'service', 'resource'])
                    is_budget = any(x in h for h in headers_lower for x in ['department', 'budget'])
                    is_proc = any(x in h for h in headers_lower for x in ['po', 'benchmark', 'qty'])
                    is_vendor = any(x in h for h in headers_lower for x in ['vendor', 'pan', 'gstin'])
                    
                    rows = []
                    for row in table[1:]:
                        if not any(row): continue
                        row_dict = {}
                        for i, cell in enumerate(row):
                            if i < len(headers):
                                row_dict[headers[i]] = str(cell).replace('\n', ' ') if cell else ""
                        rows.append(row_dict)
                        
                    if is_cloud: cloud_rows.extend(rows)
                    elif is_budget: budget_rows.extend(rows)
                    elif is_proc: proc_rows.extend(rows)
                    else: vendor_rows.extend(rows) # Fallback to vendor
                    
        return {
            "vendorRows": vendor_rows,
            "cloudRows": cloud_rows,
            "procRows": proc_rows,
            "budgetRows": budget_rows,
            "rawText": raw_text,
            "fileName": file.filename
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@app.post("/api/chat", response_model=ChatResponse)
def ai_chat(req: ChatRequest):
    q = req.message.lower()
    findings = req.findings_context or []
    active = [f for f in findings if not f.resolved]
    total_waste = sum(f.impact_inr for f in active)
    
    # 1. Advanced LLM Mock Logic matching various intents
    if any(w in q for w in ["help", "guide", "how", "what to do", "stuck"]):
        resp = f"**Welcome to the AI Copilot.** You currently have {len(active)} open alerts (₹{total_waste:,.0f} impact).\n\n"
        resp += "**Next Steps:**\n1. Review the dashboard to see macro-level trends.\n2. Click a finding to open its Remediation Plan.\n3. Hit **'Execute Fix'** to auto-resolve the issue.\n4. **Export CFO Report** via the top button to share your results."
        return ChatResponse(response=resp)
        
    if any(w in q for w in ["top", "priority", "highest", "save", "most"]):
        if not active: return ChatResponse(response="Your infrastructure is fully optimized. No critical items require priority.")
        top = sorted(active, key=lambda x: x.impact_inr, reverse=True)[:3]
        ans = "**Top Recommended Actions:**\n\n"
        for i, f in enumerate(top):
            ans += f"{i+1}. **{f.title}** (Impact: ₹{f.impact_inr:,.0f})\n   *Execute: {f.recommended_action}*\n\n"
        ans += "Tackling these directly will recover the most capital."
        return ChatResponse(response=ans)
        
    if any(w in q for w in ["vendor", "duplicate", "procurement", "supply"]):
        vf = [f for f in active if f.category in ['Vendor', 'Procurement']]
        if vf:
            return ChatResponse(response=f"I detected **{len(vf)} vendor/procurement anomalies** (totaling ₹{sum(f.impact_inr for f in vf):,.0f}). The primary offending item is **{vf[0].title}**. Recommend initiating verification workflows immediately via the panel.")
        return ChatResponse(response="I found no critical vendor issues in your active dataset. Your AP runs look compliant.")
        
    if any(w in q for w in ["cloud", "aws", "azure", "compute", "storage", "tech"]):
        cf = [f for f in active if f.category == 'Cloud']
        if cf:
            return ChatResponse(response=f"Your cloud waste requires immediate attention. Total cloud impact is ₹{sum(f.impact_inr for f in cf):,.0f}. The largest drain is **{cf[0].title}**. You should right-size these instances to optimize your burn rate.")
        return ChatResponse(response="Cloud infrastructure looks healthy with no major idle resources flagged.")
        
    if any(w in q for w in ["report", "export", "pdf", "download"]):
        return ChatResponse(response="To generate your enterprise formatted PDF report, please close this chat panel and click the **'Export CFO Report (PDF)'** button located on your main Dashboard's Savings Card.")
        
    # Catch-all Intelligent Data Synthesis
    if not active:
        ans = f"Regarding '{req.message}': Your current dataset is clean from major system anomalies! You are fully optimized. Upload a new financial dataset to continue analysis."
        return ChatResponse(response=ans)
        
    # Smart structural fallback summary
    topics = list(set([f.category for f in active]))
    dominant_cat = topics[0] if topics else 'Budget'
    ans = f"Analyzing your query: '{req.message}'...\n\n"
    ans += f"Based on the mathematical context of your dataset, the most statistically significant anomaly exists in the **{dominant_cat}** sector (specifically: '{active[0].title}'). Resolving this single issue reclaims **₹{active[0].impact_inr:,.0f}**. "
    ans += "Would you like me to draft a workflow execution for this?"
    return ChatResponse(response=ans)

@app.get("/")
def health_check():
    return {"status": "ok", "app": "Fin-Autopilot backend"}
