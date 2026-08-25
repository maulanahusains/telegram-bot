from __future__ import annotations

from fnmatch import fnmatchcase
from html import escape
from typing import Any


def branch_matches(branch: str | None, patterns: list[str]) -> bool:
    if not patterns:
        return True
    if branch is None:
        return False
    branch_parts = branch.split("/")
    for pattern in patterns:
        pattern_parts = pattern.split("/")
        if len(pattern_parts) != len(branch_parts):
            continue
        if all(fnmatchcase(actual, part) for part, actual in zip(pattern_parts, branch_parts, strict=True)):
            return True
    return False


def project_text(project: Any) -> str:
    return f"<b>{escape(project.namespace_path)}</b>"


def mr_text(project: Any, mr: dict[str, Any], *, event: str | None = None) -> str:
    author = (mr.get("author") or {}).get("name") or (mr.get("author") or {}).get("username") or "unknown"
    pipeline = (mr.get("pipeline") or {}).get("status") or "unknown"
    approval = "approved" if mr.get("approved") else "approval pending"
    prefix = f"<b>{escape(event)}</b>\n" if event else ""
    return (
        f"{prefix}{project_text(project)}\n"
        f"MR !{mr.get('iid')}: <a href=\"{escape(str(mr.get('web_url') or ''), quote=True)}\">{escape(str(mr.get('title') or ''))}</a>\n"
        f"{escape(str(mr.get('source_branch') or ''))} → {escape(str(mr.get('target_branch') or ''))}\n"
        f"Author: {escape(str(author))}\nPipeline: <code>{escape(str(pipeline))}</code> · {escape(approval)}\n"
        f"State: <code>{escape(str(mr.get('state') or 'unknown'))}</code>"
    )


def pipeline_text(project: Any, payload: dict[str, Any]) -> str:
    status = payload.get("status") or (payload.get("object_attributes") or {}).get("status") or "unknown"
    ref = payload.get("ref") or (payload.get("object_attributes") or {}).get("ref") or "unknown"
    url = payload.get("web_url") or (payload.get("object_attributes") or {}).get("url")
    link = f'<a href="{escape(str(url), quote=True)}">pipeline</a>' if url else "pipeline"
    return f"{project_text(project)}\n{link} branch <code>{escape(str(ref))}</code>: <b>{escape(str(status))}</b>"


def push_text(project: Any, payload: dict[str, Any]) -> str:
    ref = str(payload.get("ref") or "").removeprefix("refs/heads/")
    user = payload.get("user_name") or payload.get("user_username") or "unknown"
    commits = payload.get("commits") or []
    summary = "\n".join(f"• {escape(str((commit or {}).get('message', '')).splitlines()[0][:120])}" for commit in commits[:5])
    return f"{project_text(project)}\nPush oleh <b>{escape(str(user))}</b> ke <code>{escape(ref)}</code> ({len(commits)} commit)\n{summary}"


def deployment_text(project: Any, payload: dict[str, Any]) -> str:
    attrs = payload.get("deployment") or payload.get("object_attributes") or payload
    status = attrs.get("status") or "unknown"
    environment = attrs.get("environment") or attrs.get("environment_name") or "unknown"
    return f"{project_text(project)}\nDeployment <code>{escape(str(environment))}</code>: <b>{escape(str(status))}</b>"


def action_markup(actions: list[tuple[str, str]]) -> dict[str, Any] | None:
    if not actions:
        return None
    return {"inline_keyboard": [[{"text": label, "callback_data": key}] for label, key in actions]}
