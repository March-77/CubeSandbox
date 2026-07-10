# Copyright (c) 2026 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
import time
from contextvars import ContextVar, Token
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, TypeVar

MAX_STRING_LENGTH = 2048
MAX_COLLECTION_ITEMS = 50
MAX_TRACE_EVENTS = 100

_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)
_ENV_CONTAINER_KEYS = {"env", "envs", "environment", "env_vars", "envvars"}
_BEARER_RE = re.compile(r"(?i)(authorization\s*:\s*bearer\s+)\S+")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret)\b(\s*[:=]\s*)([^\s,;]+)"
)
_current_trace: ContextVar[TraceCollector | None] = ContextVar(
    "sdk_e2e_current_trace",
    default=None,
)
T = TypeVar("T")


def sanitize(value: Any, *, key: str | None = None, depth: int = 0) -> Any:
    if key and any(part in key.lower() for part in _SENSITIVE_KEY_PARTS):
        return "***"
    if depth >= 8:
        return "<max-depth>"
    if is_dataclass(value):
        return sanitize(asdict(value), depth=depth + 1)
    if isinstance(value, dict):
        items = list(value.items())
        env_container = bool(key and key.lower() in _ENV_CONTAINER_KEYS)
        named_env_item = env_container and any(
            str(item_key).lower() == "name" for item_key, _ in items
        )
        result = {
            str(item_key): (
                "***"
                if env_container
                and (
                    not named_env_item
                    or str(item_key).lower() in {"value", "valuefrom", "value_from"}
                )
                else sanitize(item_value, key=str(item_key), depth=depth + 1)
            )
            for item_key, item_value in items[:MAX_COLLECTION_ITEMS]
        }
        if len(items) > MAX_COLLECTION_ITEMS:
            result["_truncated_items"] = len(items) - MAX_COLLECTION_ITEMS
        return result
    if isinstance(value, (list, tuple, set, frozenset)):
        items = list(value)
        result = [
            sanitize(item, key=key, depth=depth + 1)
            for item in items[:MAX_COLLECTION_ITEMS]
        ]
        if len(items) > MAX_COLLECTION_ITEMS:
            result.append(f"<{len(items) - MAX_COLLECTION_ITEMS} more items>")
        return result
    if isinstance(value, bytes):
        return f"<bytes length={len(value)}>"
    if isinstance(value, str):
        redacted = _redact_text(value)
        if len(redacted) <= MAX_STRING_LENGTH:
            return redacted
        return (
            redacted[:MAX_STRING_LENGTH]
            + f"... <truncated {len(redacted) - MAX_STRING_LENGTH} chars>"
        )
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return sanitize(str(value), depth=depth + 1)


def summarize_create_options(options: dict[str, Any] | None) -> dict[str, Any]:
    options = options or {}
    summary: dict[str, Any] = {"keys": sorted(options)}
    for key in ("timeout", "lifecycle", "allow_internet_access"):
        if key in options:
            summary[key] = sanitize(options[key], key=key)
    for key in ("env_vars", "metadata"):
        value = options.get(key)
        if isinstance(value, dict):
            summary[f"{key}_keys"] = sorted(str(item) for item in value)
    network = options.get("network")
    if isinstance(network, dict):
        summary["network_keys"] = sorted(str(item) for item in network)
    return summary


def _redact_text(value: str) -> str:
    value = _BEARER_RE.sub(r"\1***", value)
    return _SECRET_ASSIGNMENT_RE.sub(r"\1\2***", value)


class TraceCollector:
    def __init__(
        self,
        nodeid: str,
        *,
        verbose: bool = False,
        emit: Callable[[str], None] | None = None,
    ) -> None:
        self.nodeid = nodeid
        self.verbose = verbose
        self._emit = emit
        self._events: list[dict[str, Any]] = []

    def capture(
        self,
        operation: str,
        inputs: dict[str, Any],
        call: Callable[[], T],
        *,
        output: Callable[[T], Any] | None = None,
    ) -> T:
        started = time.monotonic()
        try:
            result = call()
        except Exception as exc:
            self.record(
                operation,
                inputs=inputs,
                duration_ms=(time.monotonic() - started) * 1000,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        self.record(
            operation,
            inputs=inputs,
            duration_ms=(time.monotonic() - started) * 1000,
            success=True,
            output=output(result) if output else result,
        )
        return result

    def record(
        self,
        operation: str,
        *,
        inputs: Any = None,
        output: Any = None,
        duration_ms: float | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        event = sanitize(
            {
                "ts": time.time(),
                "operation": operation,
                "success": success,
                "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
                "input": inputs,
                "output": output,
                "error": error,
            }
        )
        self._events.append(event)
        if len(self._events) > MAX_TRACE_EVENTS:
            self._events.pop(0)
        if self.verbose and self._emit:
            self._emit(self.format_event(event))

    def snapshot(self) -> list[dict[str, Any]]:
        return list(self._events)

    def format_failure(self) -> str:
        if not self._events:
            return "SDK trace: no adapter operations were recorded"
        lines = ["SDK trace (most recent operations):"]
        for event in self._events[-10:]:
            lines.append(self.format_event(event))
        return "\n".join(lines)

    @staticmethod
    def format_event(event: dict[str, Any]) -> str:
        status = "ok" if event.get("success") else "failed"
        duration = event.get("duration_ms")
        detail = event.get("error") or event.get("output")
        return (
            f"[sdk-e2e] {event.get('operation')} {status} "
            f"duration_ms={duration} input={event.get('input')!r} output={detail!r}"
        )


def get_current_trace() -> TraceCollector | None:
    return _current_trace.get()


def set_current_trace(trace: TraceCollector) -> Token:
    return _current_trace.set(trace)


def reset_current_trace(token: Token) -> None:
    _current_trace.reset(token)
