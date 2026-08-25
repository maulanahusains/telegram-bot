from __future__ import annotations

import ipaddress
import socket
from base64 import b64decode
from collections.abc import AsyncIterator
from urllib.parse import quote, urlsplit, urlunsplit

import httpx

from app.modules.gitlab_ops.schemas import (
    GitlabApiError,
    GitlabBranchValue,
    GitlabMergeRequestValue,
    GitlabPipelineValue,
    GitlabProjectValue,
    GitlabUserValue,
)


def normalize_gitlab_url(value: str, *, allow_private_hosts: set[str] | None = None) -> str:
    raw = value.strip()
    parsed = urlsplit(raw)
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("GitLab base URL harus HTTPS dan tidak boleh mengandung kredensial.")
    host = parsed.hostname.rstrip(".").lower()
    allowed = {item.rstrip(".").lower() for item in (allow_private_hosts or set())}
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    resolved_addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    if address is None:
        try:
            resolved_addresses = {ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        except OSError as error:
            raise ValueError("Host GitLab tidak dapat di-resolve.") from error
    blocked = (address is not None and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved)) or any(item.is_private or item.is_loopback or item.is_link_local or item.is_reserved for item in resolved_addresses)
    if host in {"localhost", "localhost.localdomain"} or blocked:
        if host not in allowed:
            raise ValueError("Host GitLab internal/private harus masuk allowlist deployment terlebih dahulu.")
    path = parsed.path.rstrip("/")
    if path.endswith("/api/v4"):
        path = path[:-7].rstrip("/")
    return urlunsplit(("https", host, path, "", ""))


class GitlabApiClient:
    def __init__(self, http: httpx.AsyncClient, base_url: str, token: str) -> None:
        self._http = http
        self.base_url = normalize_gitlab_url(base_url)
        self._api_url = f"{self.base_url}/api/v4"
        self._token = token

    async def current_user(self) -> GitlabUserValue:
        return GitlabUserValue.model_validate(await self._request("GET", "/user"))

    async def projects(self) -> AsyncIterator[GitlabProjectValue]:
        page = 1
        while True:
            values = await self._request("GET", "/projects", params={"membership": "true", "per_page": 100, "page": page, "order_by": "path"})
            if not isinstance(values, list) or not values:
                return
            for value in values:
                yield GitlabProjectValue.model_validate(value)
            if len(values) < 100:
                return
            page += 1

    async def branches(self, project_id: int | str) -> list[GitlabBranchValue]:
        values = await self._request("GET", f"/projects/{project_id}/repository/branches", params={"per_page": 100})
        return [GitlabBranchValue.model_validate(value) for value in values]

    async def branch(self, project_id: int | str, branch: str) -> GitlabBranchValue:
        value = await self._request("GET", f"/projects/{project_id}/repository/branches/{quote(branch, safe='')}")
        return GitlabBranchValue.model_validate(value)

    async def repository_file(self, project_id: int | str, file_path: str, *, ref: str) -> str:
        value = await self._request("GET", f"/projects/{project_id}/repository/files/{quote(file_path, safe='')}", params={"ref": ref})
        try:
            return b64decode(str(value["content"])).decode("utf-8")
        except (KeyError, ValueError, UnicodeDecodeError) as error:
            raise GitlabApiError(502, "GitLab returned an invalid CI configuration file") from error

    async def ci_lint(self, project_id: int | str, *, content: str, ref: str) -> dict:
        return await self._request(
            "POST",
            f"/projects/{project_id}/ci/lint",
            json={"content": content, "ref": ref, "dry_run": True, "include_merged_yaml": True, "include_jobs": True},
        )

    async def effective_manual_jobs(self, project_id: int | str, *, ref: str) -> list[dict]:
        content = await self.repository_file(project_id, ".gitlab-ci.yml", ref=ref)
        result = await self.ci_lint(project_id, content=content, ref=ref)
        if result.get("valid") is False:
            errors = result.get("errors") or result.get("warnings") or ["CI configuration is invalid"]
            error_text = "; ".join(str(error) for error in errors) if isinstance(errors, list) else str(errors)
            raise GitlabApiError(422, error_text[:500])
        jobs = result.get("jobs") or []
        return [job for job in jobs if isinstance(job, dict) and str(job.get("when", "")) == "manual" and isinstance(job.get("name"), str)]

    async def project_hooks(self, project_id: int | str) -> list[dict]:
        return await self._request("GET", f"/projects/{project_id}/hooks", params={"per_page": 100})

    async def create_hook(self, project_id: int | str, *, url: str, token: str, trigger_config: dict[str, bool]) -> dict:
        return await self._request(
            "POST",
            f"/projects/{project_id}/hooks",
            json={"url": url, "token": token, "enable_ssl_verification": True, **trigger_config},
        )

    async def update_hook(self, project_id: int | str, hook_id: int, *, url: str, token: str, trigger_config: dict[str, bool]) -> dict:
        return await self._request(
            "PUT",
            f"/projects/{project_id}/hooks/{hook_id}",
            json={"url": url, "token": token, "enable_ssl_verification": True, **trigger_config},
        )

    async def merge_requests(self, project_id: int | str, *, state: str = "opened", source_branch: str | None = None, target_branch: str | None = None) -> list[GitlabMergeRequestValue]:
        params: dict[str, str | int] = {"state": state, "per_page": 100, "order_by": "updated_at", "sort": "desc"}
        if source_branch:
            params["source_branch"] = source_branch
        if target_branch:
            params["target_branch"] = target_branch
        values = await self._request("GET", f"/projects/{project_id}/merge_requests", params=params)
        return [GitlabMergeRequestValue.model_validate(value) for value in values]

    async def merge_request(self, project_id: int | str, iid: int) -> GitlabMergeRequestValue:
        return GitlabMergeRequestValue.model_validate(await self._request("GET", f"/projects/{project_id}/merge_requests/{iid}"))

    async def create_merge_request(self, project_id: int | str, *, source_branch: str, target_branch: str, title: str) -> GitlabMergeRequestValue:
        return GitlabMergeRequestValue.model_validate(await self._request("POST", f"/projects/{project_id}/merge_requests", json={"source_branch": source_branch, "target_branch": target_branch, "title": title}))

    async def approvals(self, project_id: int | str, iid: int) -> dict:
        return await self._request("GET", f"/projects/{project_id}/merge_requests/{iid}/approvals")

    async def approve(self, project_id: int | str, iid: int, *, sha: str) -> dict:
        return await self._request("POST", f"/projects/{project_id}/merge_requests/{iid}/approve", json={"sha": sha})

    async def merge(self, project_id: int | str, iid: int, *, sha: str) -> dict:
        return await self._request("PUT", f"/projects/{project_id}/merge_requests/{iid}/merge", json={"sha": sha, "should_remove_source_branch": False})

    async def pipelines(self, project_id: int | str, *, ref: str | None = None) -> list[GitlabPipelineValue]:
        params: dict[str, str | int] = {"per_page": 20, "order_by": "updated_at", "sort": "desc"}
        if ref:
            params["ref"] = ref
        values = await self._request("GET", f"/projects/{project_id}/pipelines", params=params)
        return [GitlabPipelineValue.model_validate(value) for value in values]

    async def create_pipeline(self, project_id: int | str, *, ref: str) -> GitlabPipelineValue:
        value = await self._request("POST", f"/projects/{project_id}/pipeline", json={"ref": ref})
        return GitlabPipelineValue.model_validate(value)

    async def pipeline_jobs(self, project_id: int | str, pipeline_id: int) -> list[dict]:
        return await self._request("GET", f"/projects/{project_id}/pipelines/{pipeline_id}/jobs", params={"per_page": 100})

    async def job(self, project_id: int | str, job_id: int) -> dict:
        return await self._request("GET", f"/projects/{project_id}/jobs/{job_id}")

    async def play_job(self, project_id: int | str, job_id: int) -> dict:
        return await self._request("POST", f"/projects/{project_id}/jobs/{job_id}/play")

    async def _request(self, method: str, path: str, **kwargs):
        headers = {"PRIVATE-TOKEN": self._token, "Accept": "application/json"}
        try:
            response = await self._http.request(method, f"{self._api_url}{path}", headers=headers, timeout=httpx.Timeout(20.0, connect=5.0), **kwargs)
        except httpx.TimeoutException as error:
            raise GitlabApiError(599, "GitLab request timed out") from error
        except httpx.HTTPError as error:
            raise GitlabApiError(598, "GitLab request failed") from error
        if response.status_code >= 400:
            retry_after = response.headers.get("Retry-After")
            try:
                retry_seconds = int(retry_after) if retry_after else None
            except ValueError:
                retry_seconds = None
            raise GitlabApiError(response.status_code, self._error_message(response), retry_after=retry_seconds)
        try:
            return response.json()
        except ValueError as error:
            raise GitlabApiError(502, "GitLab returned invalid JSON") from error

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return f"GitLab HTTP {response.status_code}"
        message = body.get("message") if isinstance(body, dict) else None
        if isinstance(message, dict):
            message = "; ".join(f"{key}: {value}" for key, value in message.items())
        return str(message or f"GitLab HTTP {response.status_code}")[:500]
