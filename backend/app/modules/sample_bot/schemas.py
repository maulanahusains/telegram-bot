from __future__ import annotations

from enum import StrEnum


class SampleCommand(StrEnum):
    START = "/start"
    PING = "/ping"
    ME = "/me"
    COUNTER = "/counter"

