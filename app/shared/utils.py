from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


def keyed_fingerprint(key: str, *values: str) -> str:
    payload = json.dumps(values, separators=(",", ":"), ensure_ascii=True).encode()
    return hmac.new(key.encode(), payload, hashlib.sha256).hexdigest()


def constant_time_equal(actual: str, expected: str) -> bool:
    return hmac.compare_digest(actual.encode(), expected.encode())


def safe_error_summary(error: BaseException, limit: int = 500) -> str:
    summary = f"{type(error).__name__}: {str(error)}"
    lowered = summary.lower()
    if any(key in lowered for key in ("token=", "secret=", "authorization:")):
        return type(error).__name__
    return summary[:limit]


def json_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
