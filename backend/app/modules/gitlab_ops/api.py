from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.registry import RuntimeBotRegistry
from app.modules.gitlab_ops.bot import GitlabOpsBot

router = APIRouter(prefix="/webhooks/gitlab", tags=["gitlab-ops"])


@router.post("/{route_key}")
async def receive_gitlab_webhook(route_key: str, request: Request) -> JSONResponse:
    container = request.app.state.container
    runtime = _runtime(container.runtimes)
    body = await _read_limited_body(request, container.settings.webhook_body_limit_bytes)
    headers = {key.lower(): value for key, value in request.headers.items()}
    accepted = await runtime.service.ingest_webhook(route_key=route_key, headers=headers, raw_body=body)
    if not accepted:
        return JSONResponse(status_code=401, content={"ok": False})
    return JSONResponse(status_code=202, content={"ok": True})


def _runtime(runtimes: RuntimeBotRegistry) -> GitlabOpsBot:
    for runtime in runtimes.bots.values():
        if isinstance(runtime.bot, GitlabOpsBot):
            return runtime.bot
    raise RuntimeError("GitLab Ops bot runtime is unavailable")


async def _read_limited_body(request: Request, limit: int) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > limit:
                return _too_large()
        except ValueError:
            return _bad_length()
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            return _too_large()
        chunks.append(chunk)
    return b"".join(chunks)


def _too_large() -> bytes:
    from starlette.exceptions import HTTPException
    raise HTTPException(status_code=413, detail="Request body is too large.")


def _bad_length() -> bytes:
    from starlette.exceptions import HTTPException
    raise HTTPException(status_code=400, detail="Invalid Content-Length.")
