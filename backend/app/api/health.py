from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.lifespan import get_container
from app.shared.responses import HealthResponse
from app.shared.utils import utc_now

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> JSONResponse:
    container = get_container(request.app)
    database_status = "healthy"
    try:
        await container.database.ping()
    except Exception:
        database_status = "unhealthy"

    if database_status == "unhealthy":
        status = "unhealthy"
        status_code = 503
    elif container.runtimes.unhealthy_count:
        status = "degraded"
        status_code = 200
    else:
        status = "healthy"
        status_code = 200
    uptime = max(int((utc_now() - container.started_at).total_seconds()), 0)
    response = HealthResponse(
        status=status,
        database=database_status,
        uptime=uptime,
        version=container.settings.app_version,
        registered_modules=len(container.modules),
        enabled_bots=container.runtimes.enabled_count,
        healthy_bots=container.runtimes.healthy_count,
        unhealthy_bots=container.runtimes.unhealthy_count,
    )
    return JSONResponse(status_code=status_code, content=response.model_dump())

