from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl

from pydantic import ValidationError

from app.core.config import Settings
from app.core.database import Database
from app.core.registry import RuntimeBot
from app.platform.auth.repositories import ApplicationSessionRepository
from app.platform.auth.schemas import AuthenticatedUser
from app.platform.users.models import BotUserStatus, TelegramUserModel
from app.platform.users.repositories import BotUserRepository, TelegramUserRepository
from app.shared.exceptions import (
    AuthenticationRequiredError,
    InvalidTelegramInitDataError,
    SessionExpiredError,
    UserBlockedError,
)
from app.shared.types import TelegramUser
from app.shared.utils import utc_now


@dataclass(frozen=True, slots=True)
class VerifiedTelegramMiniAppData:
    user: TelegramUser
    auth_date: datetime


@dataclass(frozen=True, slots=True)
class IssuedSession:
    token: str
    user: AuthenticatedUser


class TelegramMiniAppVerifier:
    @staticmethod
    def verify(
        init_data: str,
        *,
        bot_token: str,
        max_age_seconds: int,
        clock_skew_seconds: int,
    ) -> VerifiedTelegramMiniAppData:
        try:
            pairs = parse_qsl(
                init_data,
                keep_blank_values=True,
                strict_parsing=True,
                max_num_fields=32,
            )
        except ValueError as error:
            raise InvalidTelegramInitDataError from error
        if not pairs or len({key for key, _ in pairs}) != len(pairs):
            raise InvalidTelegramInitDataError

        values = dict(pairs)
        received_hash = values.pop("hash", None)
        if received_hash is None or len(received_hash) != 64:
            raise InvalidTelegramInitDataError
        try:
            int(received_hash, 16)
        except ValueError as error:
            raise InvalidTelegramInitDataError from error

        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(values.items())
        )
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()
        expected_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash.lower()):
            raise InvalidTelegramInitDataError

        auth_date_raw = values.get("auth_date")
        if auth_date_raw is None:
            raise InvalidTelegramInitDataError
        try:
            auth_date = datetime.fromtimestamp(int(auth_date_raw), tz=UTC)
        except (OverflowError, OSError, ValueError) as error:
            raise InvalidTelegramInitDataError from error
        now = utc_now()
        if auth_date > now + timedelta(seconds=clock_skew_seconds):
            raise InvalidTelegramInitDataError
        if now - auth_date > timedelta(seconds=max_age_seconds):
            raise InvalidTelegramInitDataError

        raw_user = values.get("user")
        if raw_user is None:
            raise InvalidTelegramInitDataError
        try:
            parsed_user = json.loads(raw_user)
            if not isinstance(parsed_user, dict):
                raise ValueError("Mini App user is not an object")
            user = TelegramUser.model_validate(parsed_user)
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise InvalidTelegramInitDataError from error
        if user.is_bot:
            raise InvalidTelegramInitDataError
        return VerifiedTelegramMiniAppData(user=user, auth_date=auth_date)


class PlatformAuthService:
    def __init__(self, database: Database, settings: Settings) -> None:
        self._database = database
        self._settings = settings
        self._sessions = ApplicationSessionRepository()
        self._users = TelegramUserRepository()
        self._bot_users = BotUserRepository()

    async def authenticate_telegram_mini_app(
        self, runtime: RuntimeBot, init_data: str
    ) -> IssuedSession:
        verified = TelegramMiniAppVerifier.verify(
            init_data,
            bot_token=runtime.token.get_secret_value(),
            max_age_seconds=self._settings.telegram_web_app_init_data_max_age_seconds,
            clock_skew_seconds=self._settings.telegram_web_app_clock_skew_seconds,
        )
        now = utc_now()
        expires_at = now + timedelta(
            seconds=self._settings.application_session_ttl_seconds
        )
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)
        async with self._database.transaction() as session:
            user, _ = await self._users.upsert(session, verified.user)
            bot_user, _ = await self._bot_users.resolve(
                session,
                bot_id=runtime.config.id,
                user_id=user.id,
                locale=verified.user.language_code,
            )
            if bot_user.status in (BotUserStatus.BLOCKED, BotUserStatus.DISABLED):
                raise UserBlockedError
            await self._sessions.revoke_active_for_user_and_bot(
                session,
                user_id=user.id,
                launching_bot_id=runtime.config.id,
                now=now,
            )
            await self._sessions.create(
                session,
                token_hash=token_hash,
                user_id=user.id,
                launching_bot_id=runtime.config.id,
                now=now,
                expires_at=expires_at,
            )
        return IssuedSession(
            token=token,
            user=self._authenticated_user(
                user=user,
                runtime=runtime,
                expires_at=expires_at,
            ),
        )

    async def current_user(self, token: str | None) -> AuthenticatedUser:
        if not token:
            raise AuthenticationRequiredError
        now = utc_now()
        async with self._database.transaction() as session:
            resolved = await self._sessions.find_active(
                session, token_hash=self._hash_token(token), now=now
            )
            if resolved is None:
                raise SessionExpiredError
            session_model, user, launching_bot = resolved
            session_model.last_seen_at = now
            return AuthenticatedUser(
                user_id=user.id,
                telegram_user_id=user.telegram_user_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
                launching_bot_id=launching_bot.id,
                launching_bot_name=launching_bot.name,
                launching_bot_module_name=launching_bot.module_name,
                session_expires_at=session_model.expires_at,
            )

    async def logout(self, token: str | None) -> None:
        if not token:
            return
        async with self._database.transaction() as session:
            await self._sessions.revoke_by_hash(
                session,
                token_hash=self._hash_token(token),
                now=utc_now(),
            )

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _authenticated_user(
        *, user: TelegramUserModel, runtime: RuntimeBot, expires_at: datetime
    ) -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id=user.id,
            telegram_user_id=user.telegram_user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code,
            launching_bot_id=runtime.config.id,
            launching_bot_name=runtime.config.name,
            launching_bot_module_name=runtime.config.module_name,
            session_expires_at=expires_at,
        )
