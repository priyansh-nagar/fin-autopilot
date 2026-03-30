"""
main.py – FastAPI application entry-point.
Endpoints:
  POST /api/parse    – upload CSV or PDF, returns classified row data
  POST /api/detect   – run anomaly detection on structured data
  POST /api/analyze  – full pipeline: parse → clean → classify → analyze
  POST /api/chat     – FinBot AI assistant (requires NVIDIA_API_KEY)
  GET  /             – health check
"""

from __future__ import annotations

import io
import json
import logging
import os
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw):
        return False

try:
    from openai import OpenAI as _OpenAI
except ImportError:
    _OpenAI = None

from parser import parse_file
from cleaner import classify_and_clean, clean_dataframe, normalize_records_for_frontend
from analyzer import run_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

app = FastAPI(title="Fin-Autopilot API")

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["http://localhost:5000", "http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.replit\.dev",
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "vendor":      ["invoice", "vendor", "gstin", "pan", "supplier", "inv_id", "bill"],
    "cloud":       ["ec2", "s3", "rds", "lambda", "aws", "gcp", "cloud", "cloudfront", "azure"],
    "procurement": ["po_id", "unit_price", "benchmark", "item description", "purchase order", "unit price"],
    "budget":      ["budget", "actual", "variance", "department", "cost_centre", "bgt", "q1 budget", "q2 budget"],
    "transaction": ["debit party", "credit party", "debit", "credit", "txn id", "narration", "balance"],
}


def _detect_category(columns: list[str]) -> str:
    # Build two representations of columns: with spaces (original lower) and with underscores
    col_text_space = " ".join(str(c).strip().lower() for c in columns)
    col_text_under = " ".join(str(c).strip().lower().replace(" ", "_") for c in columns)

    def score(kws: list[str]) -> int:
        return sum(1 for kw in kws if kw in col_text_space or kw.replace(" ", "_") in col_text_under)

    scores = {cat: score(kws) for cat, kws in CATEGORY_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unclassified"


def _safe_float(row: dict, candidates: list[str], default: float = 0.0) -> float:
    for key in candidates:
        for k in row:
            if key in str(k).lower():
                try:
                    return float(str(row[k]).replace(",", "").replace("₹", "").strip())
                except (TypeError, ValueError):
                    continue
    return default


def _safe_text(row: dict, candidates: list[str], default: str = "") -> str:
    for key in candidates:
        for k in row:
            if key in str(k).lower():
                v = row[k]
                if v is not None and str(v).strip() not in ("", "nan"):
                    return str(v).strip()
    return default


# ---------------------------------------------------------------------------
# POST /api/parse  – legacy-compatible file upload
# ---------------------------------------------------------------------------

DATA_TEMPLATE = {
    "vendor": [], "cloud": [], "procurement": [],
    "budget": [], "transaction": [], "unclassified": []
}


@app.post("/api/parse")
async def parse_endpoint(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith((".csv", ".pdf")):
        raise HTTPException(status_code=400, detail="Only CSV or PDF files are supported")

    content = await file.read()

    try:
        result = parse_file(content, file.filename or "uploaded")
    except Exception as exc:
        logger.exception("parse_file error")
        raise HTTPException(status_code=500, detail=f"Parse failed: {exc}") from exc

    dfs = result["dataframes"]
    raw_text = result["raw_text"]
    debug_log = result["debug_log"]

    response: dict[str, Any] = {
        "success": True,
        "fileName": file.filename,
        "totalRows": 0,
        "rowCounts": {k: 0 for k in DATA_TEMPLATE},
        "data": {k: [] for k in DATA_TEMPLATE},
        "rawText": raw_text,
        "parserUsed": result["parser_used"],
        "debugLog": debug_log,
    }

    if not dfs:
        logger.warning("/api/parse: no DataFrames extracted; debug=%s", debug_log)
        response["success"] = False
        response["error"] = "No data could be extracted from the file. Debug: " + "; ".join(debug_log)
        return response

    for df in dfs:
        if df is None or df.empty:
            continue
        # Detect category from ORIGINAL column names (before normalization)
        category = _detect_category(df.columns.tolist())
        if category not in response["data"]:
            category = "unclassified"

        # Normalize + reshape records so the frontend can read standard field names
        try:
            records = normalize_records_for_frontend(
                df.fillna("").to_dict(orient="records"), category
            )
        except Exception as norm_err:
            logger.warning("normalize_records_for_frontend failed (%s), using raw", norm_err)
            records = df.fillna("").to_dict(orient="records")

        # Transaction data also participates in vendor/duplicate analysis
        # Map "transaction" to "vendor" in the response so frontend shows it
        # but keep raw records for the detect endpoint
        frontend_cat = "vendor" if category == "transaction" else category

        response["data"][frontend_cat].extend(records)
        response["rowCounts"][frontend_cat] = response["rowCounts"].get(frontend_cat, 0) + len(records)
        response["totalRows"] += len(records)

        logger.info("Parsed %d rows → category=%s → frontend_cat=%s", len(records), category, frontend_cat)

    return response


# ---------------------------------------------------------------------------
# POST /api/detect  – legacy-compatible anomaly detection
# ---------------------------------------------------------------------------

class DetectRequest(BaseModel):
    vendor:      list[dict[str, Any]] = Field(default_factory=list)
    cloud:       list[dict[str, Any]] = Field(default_factory=list)
    procurement: list[dict[str, Any]] = Field(default_factory=list)
    budget:      list[dict[str, Any]] = Field(default_factory=list)


def _build_clean_df(records: list[dict]) -> list[pd.DataFrame]:
    if not records:
        return []
    try:
        df = clean_dataframe(pd.DataFrame(records))
        return [df] if not df.empty else []
    except Exception as err:
        logger.warning("_build_clean_df failed: %s", err)
        return [pd.DataFrame(records)] if records else []


@app.post("/api/detect")
def detect_endpoint(req: DetectRequest):
    grouped_dfs: dict[str, list[pd.DataFrame]] = {
        "vendor":      _build_clean_df(req.vendor),
        "cloud":       _build_clean_df(req.cloud),
        "procurement": _build_clean_df(req.procurement),
        "budget":      _build_clean_df(req.budget),
        "transaction": [],
        "unclassified": [],
    }

    analysis = run_analysis(grouped_dfs)

    # Map new-format anomalies to legacy finding format for frontend compatibility
    findings = []
    atype_to_category = {
        "duplicate_vendor":  "vendor",
        "duplicate_payment": "vendor",
        "overpricing":       "procurement",
        "budget_variance":   "budget",
        "cloud_spike":       "cloud",
        "idle_resource":     "cloud",
        "spike":             "vendor",
    }

    for i, anom in enumerate(analysis["anomalies"], start=1):
        impact = anom["impact"]
        atype = anom["type"]
        confidence = anom["confidence"]

        if confidence >= 0.85:
            severity = "critical"
        elif confidence >= 0.70:
            severity = "high"
        else:
            severity = "medium"

        findings.append({
            "id": f"F{i:03d}",
            "category": atype_to_category.get(atype, "vendor"),
            "severity": severity,
            "title": anom["description"],
            "inrImpact": impact,
            "rootCause": anom["reason"],
            "recommendation": anom["recommendation"],
            "effort": "2-8 hours",
            "sourceRows": anom["source_rows"],
            "detectorId": atype,
            "confidence": confidence,
        })

    summary = {
        cat: {
            "count": len([f for f in findings if f["category"] == cat]),
            "totalINR": int(sum(f["inrImpact"] for f in findings if f["category"] == cat)),
        }
        for cat in ["vendor", "cloud", "procurement", "budget"]
    }

    return {
        "success": True,
        "totalWasteINR": analysis["total_savings_potential"],
        "findingCount": len(findings),
        "findings": findings,
        "summary": summary,
        "analysis": analysis,
    }


# ---------------------------------------------------------------------------
# POST /api/analyze  – full pipeline (parse → clean → classify → analyze)
# ---------------------------------------------------------------------------

@app.post("/api/analyze")
async def analyze_endpoint(file: UploadFile = File(...)):
    """
    Single-shot endpoint: upload a file, get back full structured analysis.
    """
    filename = (file.filename or "").lower()
    if not filename.endswith((".csv", ".pdf")):
        raise HTTPException(status_code=400, detail="Only CSV or PDF files are supported")

    content = await file.read()

    try:
        parsed = parse_file(content, file.filename or "uploaded")
    except Exception as exc:
        logger.exception("analyze: parse_file error")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {exc}") from exc

    dfs = parsed["dataframes"]
    if not dfs:
        return {
            "success": False,
            "error": "No data extracted from file",
            "debug_log": parsed["debug_log"],
            "parser_used": parsed["parser_used"],
            "total_spend": 0,
            "anomalies": [],
            "duplicate_vendors": [],
            "overpricing_flags": [],
            "budget_issues": [],
            "recommendations": [],
        }

    try:
        grouped = classify_and_clean(dfs)
    except Exception as exc:
        logger.exception("analyze: classify_and_clean error")
        raise HTTPException(status_code=500, detail=f"Cleaning failed: {exc}") from exc

    try:
        analysis = run_analysis(grouped)
    except Exception as exc:
        logger.exception("analyze: run_analysis error")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    return {
        "success": True,
        "parser_used": parsed["parser_used"],
        "debug_log": parsed["debug_log"],
        **analysis,
    }


# ---------------------------------------------------------------------------
# POST /api/chat  – FinBot AI assistant
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages array is required")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")

    if _OpenAI is None:
        raise HTTPException(status_code=500, detail="openai package is not installed")

    try:
        client = _OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

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

        messages = [{"role": "system", "content": system_prompt}]
        for msg in req.messages:
            role = "assistant" if msg.role == "assistant" else "user"
            messages.append({"role": role, "content": msg.content})

        response = client.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct",
            messages=messages,
            max_tokens=1024,
        )

        reply = response.choices[0].message.content
        return {"success": True, "reply": reply, "role": "assistant"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /  – health check
# ---------------------------------------------------------------------------

@app.get("/")
def health_check():
    return {"status": "ok", "app": "Fin-Autopilot backend"}
