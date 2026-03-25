from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.chat import router as chat_router
from backend.routers.detect import router as detect_router
from backend.routers.parse import router as parse_router

app = FastAPI(title="Fin-Autopilot API")

origins = ["http://localhost:5173", "http://localhost:3000"]
extra = [o.strip() for o in os.getenv("FRONTEND_ORIGINS", "").split(",") if o.strip()]
origins.extend(extra)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(origins)),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parse_router)
app.include_router(detect_router)
app.include_router(chat_router)


@app.get("/")
def health():
    return {"status": "ok", "app": "Fin-Autopilot backend"}
