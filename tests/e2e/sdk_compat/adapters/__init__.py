# Copyright (c) 2026 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from adapters.base import SandboxAdapter
from adapters.cubesandbox_adapter import CubeSandboxAdapter
from adapters.e2b_adapter import E2BAdapter
from adapters.tracing_adapter import wrap_adapter
from framework.config import SdkE2EConfig
from framework.trace import get_current_trace, summarize_create_options


def create_adapter(
    backend: str,
    config: SdkE2EConfig,
    *,
    metadata: dict[str, str] | None = None,
    create_options: dict | None = None,
) -> SandboxAdapter:
    trace = get_current_trace()

    def _create() -> SandboxAdapter:
        if backend == "cubesandbox":
            return CubeSandboxAdapter.create(config, metadata=metadata, create_options=create_options)
        if backend == "e2b":
            return E2BAdapter.create(config, metadata=metadata, create_options=create_options)
        raise ValueError(f"unknown SDK E2E backend: {backend}")

    if trace is None:
        return _create()
    adapter = trace.capture(
        "create",
        {
            "backend": backend,
            "template_id": config.cube_template_id,
            "metadata_keys": sorted((metadata or {}).keys()),
            "create_options": summarize_create_options(create_options),
        },
        _create,
        output=lambda result: {"sandbox_id": result.sandbox_id},
    )
    return wrap_adapter(adapter, trace)


def connect_adapter(backend: str, sandbox_id: str, config: SdkE2EConfig) -> SandboxAdapter:
    trace = get_current_trace()

    def _connect() -> SandboxAdapter:
        if backend == "cubesandbox":
            return CubeSandboxAdapter.connect(sandbox_id, config)
        if backend == "e2b":
            return E2BAdapter.connect(sandbox_id, config)
        raise ValueError(f"unknown SDK E2E backend: {backend}")

    if trace is None:
        return _connect()
    adapter = trace.capture(
        "connect",
        {"backend": backend, "sandbox_id": sandbox_id},
        _connect,
        output=lambda result: {"sandbox_id": result.sandbox_id},
    )
    return wrap_adapter(adapter, trace)


def list_sandboxes(backend: str, config: SdkE2EConfig) -> list[dict]:
    trace = get_current_trace()

    def _list() -> list[dict]:
        if backend == "cubesandbox":
            return CubeSandboxAdapter.list_sandboxes(config)
        if backend == "e2b":
            return E2BAdapter.list_sandboxes(config)
        raise ValueError(f"unknown SDK E2E backend: {backend}")

    if trace is None:
        return _list()
    return trace.capture(
        "list_sandboxes",
        {"backend": backend},
        _list,
        output=lambda entries: {
            "count": len(entries),
            "sandboxes": [
                {
                    "sandbox_id": entry.get("sandboxID") or entry.get("sandbox_id"),
                    "state": entry.get("state"),
                }
                for entry in entries
                if isinstance(entry, dict)
            ],
        },
    )


__all__ = ["SandboxAdapter", "connect_adapter", "create_adapter", "list_sandboxes"]
