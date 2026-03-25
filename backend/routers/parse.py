from __future__ import annotations

import asyncio

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
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Please upload a file under 25MB.")
    try:
        parser = parse_csv if name.endswith(".csv") else parse_pdf
        return await asyncio.wait_for(
            asyncio.to_thread(parser, content, file.filename or ("uploaded.csv" if name.endswith(".csv") else "uploaded.pdf")),
            timeout=90,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Parsing timed out. Try a smaller/simpler PDF or upload CSV.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Parse failed: {exc}") from exc
