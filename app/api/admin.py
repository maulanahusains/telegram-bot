from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.lifespan import get_container
from app.platform.bots.schemas import (
    BotModuleList,
    BotMutationResponse,
    BotPatch,
    BotPublic,
    BotUpsert,
)
from app.platform.bots.services import BotConfigService
from app.shared.exceptions import InvalidAdminAPIKeyError, InvalidBotModuleError

router = APIRouter(prefix="/admin", tags=["Bot management"])
bearer = HTTPBearer(auto_error=False)


async def require_admin(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer)
    ],
) -> None:
    expected = get_settings().admin_api_key.get_secret_value()
    provided = credentials.credentials if credentials is not None else ""
    if not expected or not secrets.compare_digest(provided, expected):
        raise InvalidAdminAPIKeyError


Admin = Annotated[None, Depends(require_admin)]


@router.get("/modules", response_model=BotModuleList)
async def list_modules(request: Request, _admin: Admin) -> BotModuleList:
    modules = sorted(get_container(request.app).modules.factories)
    return BotModuleList(modules=modules)


@router.get("/bots", response_model=list[BotPublic])
async def list_bots(request: Request, _admin: Admin) -> list[BotPublic]:
    container = get_container(request.app)
    service = BotConfigService.from_settings(container.database, container.settings)
    return await service.list_public()


@router.post(
    "/bots",
    response_model=BotMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bot(
    data: BotUpsert, request: Request, _admin: Admin
) -> BotMutationResponse:
    container = get_container(request.app)
    if data.module_name not in container.modules.factories:
        raise InvalidBotModuleError(f"Unknown module: {data.module_name}")
    service = BotConfigService.from_settings(container.database, container.settings)
    bot = await service.create(data)
    return BotMutationResponse(bot=bot)


@router.patch("/bots/{name}", response_model=BotMutationResponse)
async def update_bot(
    name: str, data: BotPatch, request: Request, _admin: Admin
) -> BotMutationResponse:
    container = get_container(request.app)
    if (
        data.module_name is not None
        and data.module_name not in container.modules.factories
    ):
        raise InvalidBotModuleError(f"Unknown module: {data.module_name}")
    service = BotConfigService.from_settings(container.database, container.settings)
    bot = await service.patch(name, data)
    return BotMutationResponse(bot=bot)
