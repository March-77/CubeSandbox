# Copyright (c) 2026 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from adapters import connect_adapter, create_adapter, list_sandboxes
from adapters.base import SandboxAdapter
from framework.config import SdkE2EConfig

PAUSED_STATES = frozenset({"paused"})
TERMINAL_STATES = frozenset({"terminated", "killed", "killing", "stopped"})
DEFAULT_IDLE_TIMEOUT = 30
IDLE_WAIT_MARGIN = 20
PLATFORM_LIFECYCLE_SKIP_REASON = (
    "platform lifecycle coordinator did not act within the configured window; "
    "ensure cube-lifecycle-manager is running, cube-proxy heartbeats are healthy, "
    "and CUBE_PROXY_NODE_IP can reach the proxy admin port "
    "(see docs/guide/lifecycle.md)"
)


from framework.models import state_from_raw


def wait_until(
    predicate: Callable[[], bool],
    *,
    timeout: float = 90,
    interval: float = 1,
    description: str = "condition",
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError(f"timed out waiting for {description} within {timeout}s")


def wait_until_state(
    adapter: SandboxAdapter,
    states: frozenset[str],
    *,
    timeout: float = 90,
    interval: float = 1,
) -> str:
    observed = "unknown"

    def _matches() -> bool:
        nonlocal observed
        observed = fetch_state(adapter)
        return observed in states

    wait_until(
        _matches,
        timeout=timeout,
        interval=interval,
        description=f"state in {sorted(states)} (last={observed!r})",
    )
    return observed


def wait_until_paused(adapter: SandboxAdapter, *, timeout: float = 90) -> str:
    return wait_until_state(adapter, PAUSED_STATES, timeout=timeout)


def idle_past_timeout(idle_timeout: int, *, margin: int = IDLE_WAIT_MARGIN) -> None:
    time.sleep(idle_timeout + margin)


def wait_for_platform_pause(
    adapter: SandboxAdapter,
    config: SdkE2EConfig,
) -> bool:
    idle_past_timeout(
        config.platform_lifecycle_idle_timeout,
        margin=config.platform_lifecycle_wait_margin,
    )
    deadline = time.monotonic() + config.platform_lifecycle_poll_timeout
    while time.monotonic() < deadline:
        if fetch_state(adapter) in PAUSED_STATES:
            return True
        time.sleep(2)
    return False


def wait_for_platform_destroy(
    adapter: SandboxAdapter,
    sandbox_id: str,
    backend: str,
    config: SdkE2EConfig,
) -> tuple[bool, dict[str, Any]]:
    idle_past_timeout(
        config.platform_lifecycle_idle_timeout,
        margin=config.platform_lifecycle_wait_margin,
    )
    details: dict[str, Any] = {}
    deadline = time.monotonic() + config.platform_lifecycle_poll_timeout
    while time.monotonic() < deadline:
        details["state"] = fetch_state(adapter)
        details["listed"] = sandbox_listed(sandbox_id, backend, config)
        if details["state"].startswith("unreachable") or details["state"] in TERMINAL_STATES:
            return True, details
        if details["listed"] is False:
            return True, details
        try:
            adapter.run_command("true", timeout=min(config.command_timeout, 5))
            details["request_failed"] = False
        except Exception as exc:  # noqa: BLE001 - backend-specific destruction errors
            details["request_failed"] = True
            details["failure"] = f"{type(exc).__name__}: {exc}"
            return True, details
        time.sleep(2)
    details["request_failed"] = False
    details["failure"] = None
    return False, details


def sandbox_listed(sandbox_id: str, backend: str, config: SdkE2EConfig) -> bool | None:
    try:
        entries = list_sandboxes(backend, config)
    except Exception:
        return None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("sandboxID") == sandbox_id or entry.get("sandbox_id") == sandbox_id:
            return True
    return False


def fetch_state(adapter: SandboxAdapter) -> str:
    try:
        info = adapter.info()
        state = state_from_raw(info.raw) or info.state
        return str(state or "unknown")
    except Exception as exc:
        return f"unreachable ({type(exc).__name__})"


def assert_connect_fails(
    sandbox_id: str,
    backend: str,
    config: SdkE2EConfig,
) -> str:
    try:
        connected = connect_adapter(backend, sandbox_id, config)
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    try:
        connected.run_command("true", timeout=config.command_timeout)
        raise AssertionError("expected connect or command to fail for killed sandbox")
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    finally:
        connected.close()


def create_control_sandbox(
    backend: str,
    config: SdkE2EConfig,
    *,
    metadata: dict[str, str] | None = None,
) -> SandboxAdapter:
    return create_adapter(
        backend,
        config,
        metadata={
            "test_suite": "sdk_compat",
            "test_role": "lifecycle_control",
            **(metadata or {}),
        },
    )


def metadata_from_info(raw: dict[str, Any]) -> dict[str, Any]:
    metadata = raw.get("metadata")
    return metadata if isinstance(metadata, dict) else {}
