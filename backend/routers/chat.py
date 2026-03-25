from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None

router = APIRouter(prefix="/api", tags=["chat"])


class Message(BaseModel):
    role: str
    content: str


class ChatPayload(BaseModel):
    messages: list[Message]
    context: dict[str, Any] = Field(default_factory=dict)


@router.post("/chat")
def chat(req: ChatPayload):
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
        context = json.dumps(req.context, ensure_ascii=False)[:4000]
        system_prompt = (
            "You are FinBot, a finance-only AI for Fin-Autopilot. "
            "Answer ONLY finance and anomaly topics. "
            "Refuse non-finance questions with scope refusal template. "
            f"Current data: {context}"
        )
        history = [{"role": "model" if m.role == "assistant" else m.role, "parts": [{"text": m.content}]} for m in req.messages[:-1]]
        chat_session = model.start_chat(history=history)
        response = chat_session.send_message(f"{system_prompt}\n\nUser query: {req.messages[-1].content}")
        return {"success": True, "reply": response.text, "role": "assistant"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
