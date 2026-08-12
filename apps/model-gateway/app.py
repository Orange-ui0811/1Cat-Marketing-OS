from __future__ import annotations

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, Response

app = FastAPI(title="1Cat Model Gateway")
UPSTREAM = os.getenv("MODEL_UPSTREAM_BASE_URL", "https://api.openai.com").rstrip("/")
SECRET_FILE = Path(os.getenv("MODEL_API_KEY_FILE", "/run/secrets/model_api_key"))


def api_key() -> str:
    if not SECRET_FILE.exists():
        raise HTTPException(503, "model API key secret is not configured")
    value = SECRET_FILE.read_text(encoding="utf-8").strip()
    if not value:
        raise HTTPException(503, "model API key secret is empty")
    return value


@app.get("/health/live")
def live():
    return {"status": "ok", "secret_configured": SECRET_FILE.exists()}


@app.api_route("/v1/{path:path}", methods=["GET", "POST"])
async def proxy(path: str, request: Request):
    allowed = {"models", "chat/completions", "responses"}
    if path not in allowed:
        raise HTTPException(404, "model route not allowed")
    body = await request.body()
    headers = {"Authorization": f"Bearer {api_key()}", "Content-Type": request.headers.get("content-type", "application/json")}
    async with httpx.AsyncClient(timeout=180) as client:
        result = await client.request(request.method, f"{UPSTREAM}/v1/{path}", content=body, headers=headers)
    return Response(content=result.content, status_code=result.status_code, media_type=result.headers.get("content-type"))

