import io
import json
import os
import tempfile
from collections import defaultdict
from datetime import timedelta
from itertools import combinations
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False

try:
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover
    import difflib

    class _Fuzz:
        @staticmethod
        def token_sort_ratio(a: str, b: str) -> float:
            a_sorted = " ".join(sorted(a.split()))
            b_sorted = " ".join(sorted(b.split()))
            return difflib.SequenceMatcher(None, a_sorted, b_sorted).ratio() * 100

    class _Process:
        @staticmethod
        def extractOne(query: str, choices, scorer):
            best = None
            for choice in choices:
                score = scorer(query, choice)
                if best is None or score > best[1]:
                    best = (choice, score, None)
            return best

    fuzz = _Fuzz()
    process = _Process()

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None


load_dotenv()

app = FastAPI(title="Fin-Autopilot API")

DEFAULT_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
EXTRA_ORIGINS = [o.strip() for o in os.getenv("FRONTEND_ORIGINS", "").split(",") if o.strip()]
ALLOWED_ORIGINS = list(dict.fromkeys(DEFAULT_ORIGINS + EXTRA_ORIGINS))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

CATEGORY_KEYWORDS = {
    "vendor": ["invoice", "vendor", "gstin", "pan", "amount", "inv_id"],
    "cloud": ["service", "ec2", "s3", "rds", "lambda", "aws", "gcp", "cloud"],
    "procurement": ["po_id", "unit_price", "benchmark", "item", "purchase"],
    "budget": ["budget", "actual", "department", "variance", "cost_centre"],
}

BENCHMARKS = {
    "laptop": 67500,
    "desktop": 45000,
    "monitor": 28500,
    "server": 280000,
    "printer": 44500,
    "ups": 21000,
    "chair": 16200,
    "paper_ream": 285,
    "toner": 2850,
    "zoom_seat": 10800,
    "slack_seat": 6250,
    "salesforce_seat": 98500,
    "aws_reserved_1yr": 154000,
    "diesel_litre": 94,
    "water_can": 72,
}

DATA_TEMPLATE = {
    "vendor": [],
    "cloud": [],
    "procurement": [],
    "budget": [],
    "unclassified": [],
}


def _normalize_columns(columns: list[str]) -> list[str]:
    return [str(c).strip().lower().replace(" ", "_") for c in columns]


def detect_category(columns: list[str]) -> str:
    normalized = _normalize_columns(columns)
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for col in normalized for keyword in keywords if keyword in col)
        scores[category] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unclassified"


def _safe_float(row: dict[str, Any], candidates: list[str], default: float = 0.0) -> float:
    for key in candidates:
        for k in row.keys():
            if key in str(k).lower():
                value = row.get(k)
                try:
                    return float(str(value).replace(",", "").strip())
                except (TypeError, ValueError):
                    continue
    return default


def _safe_text(row: dict[str, Any], candidates: list[str], default: str = "") -> str:
    for key in candidates:
        for k in row.keys():
            if key in str(k).lower():
                value = row.get(k)
                if value is not None and str(value).strip() != "":
                    return str(value).strip()
    return default


def _base_response(file_name: str, raw_text: str = "") -> dict[str, Any]:
    return {
        "success": True,
        "fileName": file_name,
        "totalRows": 0,
        "rowCounts": {k: 0 for k in DATA_TEMPLATE},
        "data": {k: [] for k in DATA_TEMPLATE},
        "rawText": raw_text,
    }


@app.post("/api/parse")
@app.post("/parse")
async def parse_file(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith((".csv", ".pdf")):
        raise HTTPException(status_code=400, detail="Only CSV or PDF files are supported")

    try:
        content = await file.read()
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
            records = df.fillna("").to_dict(orient="records")
            category = detect_category(df.columns.tolist())
            response = _base_response(file.filename or "uploaded.csv")
            response["data"][category] = records
            response["rowCounts"][category] = len(records)
            response["totalRows"] = len(records)
            return response

        if pdfplumber is None:
            raise HTTPException(status_code=500, detail="PDF parsing dependency pdfplumber is not installed")

        response = _base_response(file.filename or "uploaded.pdf")
        raw_text_parts: list[str] = []
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(content)
            tmp.flush()
            with pdfplumber.open(tmp.name) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text:
                        raw_text_parts.append(page_text)
                    tables = page.extract_tables() or []
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(table[0])]
                        rows: list[dict[str, Any]] = []
                        for row in table[1:]:
                            if not row or not any(cell for cell in row):
                                continue
                            row_dict = {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}
                            rows.append(row_dict)
                        category = detect_category(headers)
                        response["data"][category].extend(rows)

        response["rawText"] = "\n".join(raw_text_parts)
        response["rowCounts"] = {k: len(v) for k, v in response["data"].items()}
        response["totalRows"] = sum(response["rowCounts"].values())
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Parse failed: {exc}") from exc


class DetectRequest(BaseModel):
    vendor: list[dict[str, Any]] = Field(default_factory=list)
    cloud: list[dict[str, Any]] = Field(default_factory=list)
    procurement: list[dict[str, Any]] = Field(default_factory=list)
    budget: list[dict[str, Any]] = Field(default_factory=list)


def vendor_duplicates(vendor_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings = []
    groups = defaultdict(list)
    for idx, row in enumerate(vendor_rows):
        tax_id = _safe_text(row, ["pan", "gstin"])
        vendor_name = _safe_text(row, ["vendor", "name", "supplier"], "Unknown Vendor")
        groups[(tax_id or "", vendor_name.lower())].append((idx, row))

    by_tax = defaultdict(list)
    for idx, row in enumerate(vendor_rows):
        by_tax[_safe_text(row, ["pan", "gstin"])].append((idx, row))

    for tax_id, members in by_tax.items():
        if tax_id and len(members) > 1:
            impact = int(sum(_safe_float(r, ["amount", "invoice", "total"]) for _, r in members))
            findings.append(
                {
                    "category": "vendor",
                    "severity": "critical",
                    "title": f"Duplicate vendor tax identity detected ({tax_id})",
                    "inrImpact": impact,
                    "rootCause": "Multiple rows share same PAN/GSTIN, indicating duplicate vendor records.",
                    "recommendation": "Consolidate vendor master entries and block duplicate invoice posting.",
                    "effort": "4-8 hours",
                    "sourceRows": [i for i, _ in members],
                    "detectorId": "A",
                }
            )

    for (i, left), (j, right) in combinations(list(enumerate(vendor_rows)), 2):
        name_left = _safe_text(left, ["vendor", "name", "supplier"]).strip()
        name_right = _safe_text(right, ["vendor", "name", "supplier"]).strip()
        if not name_left or not name_right or name_left.lower() == name_right.lower():
            continue
        score = fuzz.token_sort_ratio(name_left, name_right)
        if score >= 85:
            pan_left = _safe_text(left, ["pan", "gstin"])
            pan_right = _safe_text(right, ["pan", "gstin"])
            impact = int(
                _safe_float(left, ["amount", "invoice", "total"])
                + _safe_float(right, ["amount", "invoice", "total"])
            )
            findings.append(
                {
                    "category": "vendor",
                    "severity": "critical" if pan_left and pan_right and pan_left == pan_right else "medium",
                    "title": f"Potential duplicate vendors: {name_left} / {name_right}",
                    "inrImpact": impact,
                    "rootCause": f"Vendor names fuzzy-match at {score:.0f}%.",
                    "recommendation": "Validate KYC and merge duplicate vendors.",
                    "effort": "2-4 hours",
                    "sourceRows": [i, j],
                    "detectorId": "A",
                }
            )
    return findings


def cloud_spikes(cloud_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings = []
    if not cloud_rows:
        return findings
    df = pd.DataFrame(cloud_rows)
    if df.empty:
        return findings

    date_col = next((c for c in df.columns if "date" in c.lower() or "month" in c.lower()), None)
    service_col = next((c for c in df.columns if "service" in c.lower()), None)
    spend_col = next((c for c in df.columns if any(x in c.lower() for x in ["cost", "spend", "amount"])), None)
    usage_col = next((c for c in df.columns if "usage" in c.lower() or "utilization" in c.lower()), None)

    if date_col and service_col and spend_col:
        df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
        df["_spend"] = pd.to_numeric(df[spend_col], errors="coerce").fillna(0)
        df = df.dropna(subset=["_date"]).sort_values("_date")
        for service, group in df.groupby(service_col):
            group = group.sort_values("_date").copy()
            group["rolling_mean"] = group.set_index("_date")["_spend"].rolling("30D", min_periods=1).mean().values
            spikes = group[group["_spend"] > 2.5 * group["rolling_mean"]]
            if not spikes.empty:
                spike_days = max(len(spikes), 1)
                waste = int(((spikes["_spend"] - spikes["rolling_mean"]).clip(lower=0).sum()) * spike_days)
                findings.append(
                    {
                        "category": "cloud",
                        "severity": "high",
                        "title": f"Cloud spend spike detected for {service}",
                        "inrImpact": waste,
                        "rootCause": "Spend exceeded 2.5x 30-day rolling average.",
                        "recommendation": "Apply right-sizing and savings plans for this service.",
                        "effort": "4-12 hours",
                        "sourceRows": spikes.index.astype(int).tolist(),
                        "detectorId": "B",
                    }
                )

            if usage_col:
                idle = group[(pd.to_numeric(group[usage_col], errors="coerce").fillna(1) == 0)]
                if len(idle) >= 60:
                    idle_waste = int(idle["_spend"].sum())
                    findings.append(
                        {
                            "category": "cloud",
                            "severity": "high",
                            "title": f"Idle {service} resources over 60 days",
                            "inrImpact": idle_waste,
                            "rootCause": "Usage remained zero for over 60 records/days.",
                            "recommendation": "Stop/decommission idle resources and enforce auto-shutdown policies.",
                            "effort": "2-6 hours",
                            "sourceRows": idle.index.astype(int).tolist(),
                            "detectorId": "B",
                        }
                    )

    return findings


def procurement_overpricing(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings = []
    for idx, row in enumerate(rows):
        item_text = _safe_text(row, ["item_description", "item", "description", "product"])
        if not item_text:
            continue
        match = process.extractOne(item_text.lower().replace(" ", "_"), BENCHMARKS.keys(), scorer=fuzz.token_sort_ratio)
        if not match:
            continue
        item_key, score, _ = match
        if score < 70:
            continue
        benchmark = BENCHMARKS[item_key]
        unit_price = _safe_float(row, ["unit_price", "price", "rate"])
        quantity = _safe_float(row, ["quantity", "qty", "units"], 1)
        if unit_price > benchmark * 1.15:
            overspend = int((unit_price - benchmark) * quantity)
            findings.append(
                {
                    "category": "procurement",
                    "severity": "high",
                    "title": f"Overpriced procurement: {item_text}",
                    "inrImpact": overspend,
                    "rootCause": f"Unit price is {(unit_price / benchmark - 1) * 100:.1f}% above benchmark ({item_key}).",
                    "recommendation": "Renegotiate with vendor or switch to benchmarked alternatives.",
                    "effort": "3-8 hours",
                    "sourceRows": [idx],
                    "detectorId": "C",
                }
            )
    return findings


def budget_variance(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings = []
    for idx, row in enumerate(rows):
        budget = _safe_float(row, ["budget"])
        actual = _safe_float(row, ["actual", "spend"])
        if budget <= 0:
            continue
        variance_pct = ((actual - budget) / budget) * 100
        if variance_pct > 30:
            severity = "critical"
            label = "critical"
        elif variance_pct > 10:
            severity = "medium"
            label = "watch"
        else:
            continue
        impact = int(max(actual - budget, 0))
        dept = _safe_text(row, ["department", "cost_centre", "cost_center"], "Unknown Department")
        findings.append(
            {
                "category": "budget",
                "severity": severity,
                "title": f"{dept} budget variance is {variance_pct:.1f}% ({label})",
                "inrImpact": impact,
                "rootCause": "Actuals are materially higher than budget plan.",
                "recommendation": "Launch monthly budget controls and approval gates.",
                "effort": "2-6 hours",
                "sourceRows": [idx],
                "detectorId": "D",
            }
        )
    return findings


@app.post("/api/detect")
@app.post("/detect")
def detect(req: DetectRequest):
    findings = []
    findings.extend(vendor_duplicates(req.vendor))
    findings.extend(cloud_spikes(req.cloud))
    findings.extend(procurement_overpricing(req.procurement))
    findings.extend(budget_variance(req.budget))

    findings.sort(key=lambda f: f["inrImpact"], reverse=True)
    for i, finding in enumerate(findings, start=1):
        finding["id"] = f"F{i:03d}"

    summary = {
        category: {
            "count": len([f for f in findings if f["category"] == category]),
            "totalINR": int(sum(f["inrImpact"] for f in findings if f["category"] == category)),
        }
        for category in ["vendor", "cloud", "procurement", "budget"]
    }

    return {
        "success": True,
        "totalWasteINR": int(sum(f["inrImpact"] for f in findings)),
        "findingCount": len(findings),
        "findings": findings,
        "summary": summary,
    }


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/chat")
@app.post("/chat")
def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages array is required")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    if genai is None:
        raise HTTPException(status_code=500, detail="google-generativeai is not installed")

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        context_payload = json.dumps(req.context, ensure_ascii=False)[:4000]
        system_prompt = (
            "You are FinBot, a finance-only AI for Fin-Autopilot. "
            "Answer ONLY questions about: cost anomalies, vendor duplicates, procurement overpricing, "
            "cloud waste, budget variances, GST/TDS, accounts payable/receivable, P&L, working capital, CFO reporting. "
            "Refuse ALL other topics with: 'I am FinBot, specialised in enterprise finance. That is outside my scope. "
            "Based on your data, I can help you with: [2 specific suggestions from their data].' "
            "Style: lead with INR figure, use lakh/crore, reference actual vendor names and departments from data, "
            "end with 'Recommended next action: [one action].' "
            f"Current data: {context_payload}"
        )

        history = []
        for msg in req.messages[:-1]:
            if msg.role in {"user", "assistant", "model"}:
                history.append(
                    {
                        "role": "model" if msg.role == "assistant" else msg.role,
                        "parts": [{"text": msg.content}],
                    }
                )

        chat_session = model.start_chat(history=history)
        user_prompt = f"{system_prompt}\n\nUser query: {req.messages[-1].content}"
        response = chat_session.send_message(user_prompt)

        return {"success": True, "reply": response.text, "role": "assistant"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/")
def health_check():
    return {"status": "ok", "app": "Fin-Autopilot backend"}
