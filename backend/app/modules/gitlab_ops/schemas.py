from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class GitlabUserValue(BaseModel):
    external_user_id: int = Field(validation_alias=AliasChoices("id", "external_user_id"))
    username: str | None = None
    name: str | None = None


class GitlabProjectValue(BaseModel):
    id: int
    name: str
    path_with_namespace: str
    web_url: str | None = None
    default_branch: str | None = None


class GitlabBranchValue(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    protected: bool = False
    commit: dict[str, Any] = Field(default_factory=dict)


class GitlabMergeRequestValue(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    iid: int
    title: str
    state: str
    source_branch: str
    target_branch: str
    web_url: str | None = None
    sha: str | None = None
    detailed_merge_status: str | None = None
    author: dict[str, Any] = Field(default_factory=dict)
    merge_status: str | None = None
    approved: bool | None = None
    pipeline: dict[str, Any] | None = None


class GitlabPipelineValue(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    status: str | None = None
    ref: str | None = None
    web_url: str | None = None


class GitlabApiError(Exception):
    def __init__(self, status_code: int, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class PromotionRuleInput(BaseModel):
    display_name: str = Field(min_length=1, max_length=128)
    source_branch: str = Field(min_length=1, max_length=255)
    target_branch: str = Field(min_length=1, max_length=255)
    mr_required: bool = True
    approval_required: bool = True
    successful_pipeline_required: bool = True
    manual_confirmation_required: bool = True
    production_sensitive: bool = False


class SubscriptionInput(BaseModel):
    event_categories: list[str] = Field(default_factory=lambda: ["push", "merge_request", "pipeline", "deployment"])
    pipeline_mode: Literal["failures", "all"] = "failures"
    branch_patterns: list[str] = Field(default_factory=list)

    @field_validator("branch_patterns")
    @classmethod
    def validate_patterns(cls, values: list[str]) -> list[str]:
        for value in values:
            if not value or value.startswith("/") or "**" in value or any(char in value for char in "[]{}?"):
                raise ValueError("Branch filter hanya mendukung nama branch dan * dalam satu segmen.")
            parts = value.split("/")
            if any("*" in part and part != "*" and part.count("*") > 1 for part in parts):
                raise ValueError("Branch filter memiliki pola glob yang tidak valid.")
        return values


class WebhookEventValue(BaseModel):
    event_type: str
    project_id: int | None = None
    ref: str | None = None
    branch: str | None = None
    resource_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CallbackActionValue(BaseModel):
    action_key: str
    action_type: str
    target: dict[str, Any]
    expected_sha: str | None
    expires_at: datetime


class ManualScriptJobValue(BaseModel):
    name: str
    when: str
    stage: str | None = None
    allow_failure: bool | None = None


class ManualScriptMappingInput(BaseModel):
    target_branch: str = Field(min_length=1, max_length=255)
    job_name: str = Field(min_length=1, max_length=255)
    telegram_label: str = Field(min_length=1, max_length=128)
