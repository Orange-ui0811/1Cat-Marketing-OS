from __future__ import annotations

import hmac
import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask


app = FastAPI(title="1Cat Model Gateway")
UPSTREAM = os.getenv("MODEL_UPSTREAM_BASE_URL", "https://api.deepseek.com").rstrip("/")
MODEL_ID = os.getenv("MODEL_UPSTREAM_MODEL_ID", "deepseek-v4-pro").strip()
CLIENT_TOKEN = os.getenv("MODEL_GATEWAY_CLIENT_TOKEN", "").strip()
SECRET_FILE = Path(os.getenv("MODEL_API_KEY_FILE", "/run/secrets/model_api_key"))
UPSTREAM_TIMEOUT_SECONDS = float(os.getenv("MODEL_UPSTREAM_TIMEOUT_SECONDS", "900"))


def api_key() -> str:
    if not SECRET_FILE.exists():
        raise HTTPException(503, "model API key secret is not configured")
    value = SECRET_FILE.read_text(encoding="utf-8").strip()
    if not value:
        raise HTTPException(503, "model API key secret is empty")
    return value


def require_internal_client(authorization: str | None) -> None:
    if not CLIENT_TOKEN:
        raise HTTPException(503, "model gateway client token is not configured")
    scheme, _, value = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(value, CLIENT_TOKEN):
        raise HTTPException(401, "invalid model gateway client token")


def upstream_url(path: str) -> str:
    base = UPSTREAM[:-3] if UPSTREAM.endswith("/v1") else UPSTREAM
    return f"{base}/v1/{path}"


def validate_model(path: str, body: bytes) -> None:
    if path not in {"chat/completions", "responses"} or not MODEL_ID:
        return
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "model request body must be valid JSON") from exc
    if payload.get("model") != MODEL_ID:
        raise HTTPException(400, f"model gateway only permits {MODEL_ID}")


async def close_upstream(result: httpx.Response, client: httpx.AsyncClient) -> None:
    await result.aclose()
    await client.aclose()


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    api_key()
    if not CLIENT_TOKEN:
        raise HTTPException(503, "model gateway client token is not configured")
    return {
        "status": "ready",
        "provider": "deepseek",
        "model": MODEL_ID,
        "upstream": UPSTREAM,
    }


@app.api_route("/v1/{path:path}", methods=["GET", "POST"])
async def proxy(path: str, request: Request, authorization: str | None = Header(default=None)):
    allowed = {"models", "chat/completions", "responses"}
    if path not in allowed:
        raise HTTPException(404, "model route not allowed")
    require_internal_client(authorization)
    body = await request.body()
    validate_model(path, body)
    headers = {
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": request.headers.get("content-type", "application/json"),
        "Accept": request.headers.get("accept", "application/json"),
    }
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(UPSTREAM_TIMEOUT_SECONDS, connect=30),
        follow_redirects=False,
    )
    try:
        upstream_request = client.build_request(
            request.method,
            upstream_url(path),
            content=body,
            headers=headers,
        )
        result = await client.send(upstream_request, stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(502, f"model upstream unavailable: {type(exc).__name__}") from exc

    response_headers = {}
    for name in ("content-type", "x-request-id", "request-id"):
        if value := result.headers.get(name):
            response_headers[name] = value
    return StreamingResponse(
        result.aiter_raw(),
        status_code=result.status_code,
        headers=response_headers,
        background=BackgroundTask(close_upstream, result, client),
    )

