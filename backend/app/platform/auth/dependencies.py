from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.core.lifespan import get_container
from app.platform.auth.schemas import AuthenticatedUser
from app.platform.auth.services import PlatformAuthService


async def require_authenticated_user(request: Request) -> AuthenticatedUser:
    container = get_container(request.app)
    token = request.cookies.get(container.settings.application_session_cookie_name)
    service = PlatformAuthService(container.database, container.settings)
    return await service.current_user(token)


Authenticated = Annotated[AuthenticatedUser, Depends(require_authenticated_user)]
