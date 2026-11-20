from dataclasses import dataclass
from typing import Any


@dataclass
class LLMToolResponse:
    message: Any
    model: str | None = None
    usage: dict | None = None
    finish_reason: str | None = None
    provider: str | None = None