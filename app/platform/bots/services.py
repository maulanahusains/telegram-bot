from __future__ import annotations

import re
from collections.abc import Sequence

from cryptography.fernet import Fernet, MultiFernet
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.database import Database
from app.platform.bots.repositories import BotRepository
from app.platform.bots.schemas import (
    BotConfig,
    BotDescriptor,
    BotPatch,
    BotPublic,
    BotUpsert,
)
from app.shared.exceptions import (
    BotAlreadyExistsError,
    BotNotFoundError,
    InvalidBotModuleError,
)

BOT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class CredentialCipher:
    def __init__(self, keys: Sequence[SecretStr]) -> None:
        fernets = [
            Fernet(key.get_secret_value().encode("ascii"))
            for key in keys
        ]
        self._cipher = MultiFernet(fernets)

    def encrypt(self, value: SecretStr | str) -> str:
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        return self._cipher.encrypt(raw.encode()).decode()

    def decrypt(self, value: str) -> SecretStr:
        return SecretStr(self._cipher.decrypt(value.encode()).decode())


class BotConfigService:
    def __init__(
        self,
        database: Database,
        repository: BotRepository,
        cipher: CredentialCipher,
    ) -> None:
        self._database = database
        self._repository = repository
        self._cipher = cipher

    @classmethod
    def from_settings(cls, database: Database, settings: Settings) -> BotConfigService:
        return cls(
            database=database,
            repository=BotRepository(),
            cipher=CredentialCipher(settings.credential_keys),
        )

    async def load_all(self) -> list[BotConfig]:
        async with self._database.session() as session:
            models = await self._repository.list_all(session)
        return [
            BotConfig(
                id=model.id,
                name=model.name,
                token=self._cipher.decrypt(model.token_ciphertext),
                secret_token=self._cipher.decrypt(model.secret_token_ciphertext),
                enabled=model.enabled,
                description=model.description,
                module_name=model.module_name,
                webhook_url=model.webhook_url,
                webhook_sync_fingerprint=model.webhook_sync_fingerprint,
            )
            for model in models
        ]

    async def list_public(self) -> list[BotPublic]:
        async with self._database.session() as session:
            models = await self._repository.list_all(session)
            return [BotPublic.model_validate(model) for model in models]

    async def upsert(self, data: BotUpsert) -> BotPublic:
        self._validate_name(data.name)
        self._validate_name(data.module_name)
        self._validate_secret(data.token, "Telegram token")
        self._validate_secret(data.secret_token, "Webhook secret")
        async with self._database.transaction() as session:
            model = await self._repository.upsert(
                session,
                name=data.name,
                module_name=data.module_name,
                token_ciphertext=self._cipher.encrypt(data.token),
                secret_token_ciphertext=self._cipher.encrypt(data.secret_token),
                enabled=data.enabled,
                description=data.description,
            )
            await session.flush()
            return BotPublic.model_validate(model)

    async def create(self, data: BotUpsert) -> BotPublic:
        self._validate_name(data.name)
        self._validate_name(data.module_name)
        self._validate_secret(data.token, "Telegram token")
        self._validate_secret(data.secret_token, "Webhook secret")
        try:
            async with self._database.transaction() as session:
                model = await self._repository.create(
                    session,
                    name=data.name,
                    module_name=data.module_name,
                    token_ciphertext=self._cipher.encrypt(data.token),
                    secret_token_ciphertext=self._cipher.encrypt(data.secret_token),
                    enabled=data.enabled,
                    description=data.description,
                )
                return BotPublic.model_validate(model)
        except IntegrityError as error:
            raise BotAlreadyExistsError from error

    async def set_enabled(self, name: str, enabled: bool) -> BotPublic:
        self._validate_name(name)
        async with self._database.transaction() as session:
            model = await self._repository.set_enabled(
                session, name=name, enabled=enabled
            )
            if model is None:
                raise BotNotFoundError
            await session.flush()
            return BotPublic.model_validate(model)

    async def patch(self, name: str, data: BotPatch) -> BotPublic:
        self._validate_name(name)
        values: dict[str, object] = {}
        supplied = data.model_fields_set
        if "module_name" in supplied:
            if data.module_name is None:
                raise InvalidBotModuleError("Module name cannot be null.")
            self._validate_name(data.module_name)
            values["module_name"] = data.module_name
        if "token" in supplied:
            if data.token is None:
                raise InvalidBotModuleError("Token cannot be null.")
            self._validate_secret(data.token, "Telegram token")
            values["token_ciphertext"] = self._cipher.encrypt(data.token)
        if "secret_token" in supplied:
            if data.secret_token is None:
                raise InvalidBotModuleError("Webhook secret cannot be null.")
            self._validate_secret(data.secret_token, "Webhook secret")
            values["secret_token_ciphertext"] = self._cipher.encrypt(
                data.secret_token
            )
        if "enabled" in supplied:
            if data.enabled is None:
                raise InvalidBotModuleError("Enabled cannot be null.")
            values["enabled"] = data.enabled
        if "description" in supplied:
            values["description"] = data.description
        async with self._database.transaction() as session:
            model = await self._repository.patch(session, name=name, values=values)
            if model is None:
                raise BotNotFoundError
            await session.flush()
            return BotPublic.model_validate(model)

    @staticmethod
    def descriptors(configs: Sequence[BotConfig]) -> list[BotDescriptor]:
        return [
            BotDescriptor(
                id=config.id,
                name=config.name,
                enabled=config.enabled,
                module_name=config.module_name,
                description=config.description,
            )
            for config in configs
        ]

    @staticmethod
    def _validate_name(value: str) -> None:
        if BOT_NAME_PATTERN.fullmatch(value) is None:
            raise InvalidBotModuleError(
                "Names must start with a lowercase letter and contain only "
                "lowercase letters, digits, and underscores."
            )

    @staticmethod
    def _validate_secret(value: SecretStr, label: str) -> None:
        if not value.get_secret_value().strip():
            raise InvalidBotModuleError(f"{label} cannot be empty.")
