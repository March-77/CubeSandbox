# Copyright (c) 2026 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from adapters.api_adapter import ApiClient
from adapters.base import SandboxAdapter
from framework.config import SdkE2EConfig


def safe_kill(adapter: SandboxAdapter, config: SdkE2EConfig) -> list[str]:
    """Best-effort sandbox cleanup.

    Returns diagnostic messages instead of raising, so teardown never hides the
    original test failure.
    """

    errors: list[str] = []
    kill_adapter = adapter
    try:
        try:
            state = adapter.info().state
        except Exception as exc:  # noqa: BLE001 - cleanup must continue
            state = None
            errors.append(f"{adapter.backend}.info failed for {adapter.sandbox_id}: {exc}")

        if state == "paused":
            try:
                kill_adapter = adapter.resume_or_connect(timeout=config.default_timeout)
            except Exception as exc:  # noqa: BLE001 - fallback delete handles this
                errors.append(
                    f"{adapter.backend}.resume before kill failed for "
                    f"{adapter.sandbox_id}: {exc}"
                )

        kill_adapter.kill()
    except Exception as exc:  # noqa: BLE001 - teardown must be best-effort
        errors.append(f"{kill_adapter.backend}.kill failed for {adapter.sandbox_id}: {exc}")
        api = ApiClient(config)
        try:
            api.delete_sandbox(adapter.sandbox_id)
        except Exception as api_exc:  # noqa: BLE001
            errors.append(f"REST delete failed for {adapter.sandbox_id}: {api_exc}")
        finally:
            api.close()
    finally:
        try:
            if kill_adapter is not adapter:
                kill_adapter.close()
        except Exception as exc:  # noqa: BLE001
            errors.append(
                f"{kill_adapter.backend}.close failed for {adapter.sandbox_id}: {exc}"
            )
        try:
            adapter.close()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{adapter.backend}.close failed for {adapter.sandbox_id}: {exc}")
    return errors
