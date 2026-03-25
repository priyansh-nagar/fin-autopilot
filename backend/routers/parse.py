from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.parsers.csv_parser import parse_csv
from backend.parsers.pdf_parser import parse_pdf

router = APIRouter(prefix="/api", tags=["parse"])


@router.post("/parse")
async def parse_endpoint(file: UploadFile = File(...)):
    name = (file.filename or "").lower()
    if not name.endswith((".csv", ".pdf")):
        raise HTTPException(status_code=400, detail="Only CSV or PDF files are supported")
    content = await file.read()
    try:
        return parse_csv(content, file.filename or "uploaded.csv") if name.endswith(".csv") else parse_pdf(content, file.filename or "uploaded.pdf")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Parse failed: {exc}") from exc
