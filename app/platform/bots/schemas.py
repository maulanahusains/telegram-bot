from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class BotConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    token: SecretStr
    secret_token: SecretStr
    enabled: bool
    description: str | None
    module_name: str
    webhook_url: str | None
    webhook_sync_fingerprint: str | None


class BotDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    enabled: bool
    module_name: str
    description: str | None


class BotRuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    enabled: bool
    description: str | None
    module_name: str


class BotUpsert(BaseModel):
    name: str
    module_name: str
    token: SecretStr = Field(json_schema_extra={"writeOnly": True})
    secret_token: SecretStr = Field(json_schema_extra={"writeOnly": True})
    enabled: bool = True
    description: str | None = None


class BotPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    enabled: bool
    module_name: str
    description: str | None


class BotPatch(BaseModel):
    module_name: str | None = None
    token: SecretStr | None = Field(
        default=None, json_schema_extra={"writeOnly": True}
    )
    secret_token: SecretStr | None = Field(
        default=None, json_schema_extra={"writeOnly": True}
    )
    enabled: bool | None = None
    description: str | None = None

    @model_validator(mode="after")
    def require_field(self) -> BotPatch:
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied.")
        return self


class BotMutationResponse(BaseModel):
    bot: BotPublic
    restart_required: bool = True


class BotModuleList(BaseModel):
    modules: list[str]
