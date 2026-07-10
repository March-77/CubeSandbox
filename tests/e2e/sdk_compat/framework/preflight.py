# Copyright (c) 2026 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

from adapters.api_adapter import ApiClient
from framework.config import SdkE2EConfig
from framework.platform_lifecycle import probe_platform_lifecycle
from framework.reporting import JsonlReporter


def run_preflight(config: SdkE2EConfig, reporter: JsonlReporter) -> None:
    errors: list[str] = []
    details: dict[str, Any] = {"backends": config.backends}

    if not config.cube_template_id:
        errors.append("CUBE_TEMPLATE_ID or --cube-template-id is required")

    api = ApiClient(config)
    try:
        try:
            health = api.health()
            details["health"] = health
            if health.get("status") not in (None, "ok", "healthy"):
                errors.append(f"CubeAPI health returned unexpected status: {health!r}")
        except Exception as exc:  # noqa: BLE001 - preflight should aggregate diagnostics
            errors.append(f"CubeAPI {config.cube_api_url}/health is not reachable: {exc}")

        if config.cube_template_id:
            try:
                template = api.get_template(config.cube_template_id)
                details["template"] = _template_summary(config.cube_template_id, template)
                if not template:
                    errors.append(f"template {config.cube_template_id!r} was not found")
                else:
                    _check_template_ready(config.cube_template_id, template, errors)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"failed to read template {config.cube_template_id!r}: {exc}")
    finally:
        api.close()

    if config.platform_lifecycle_enabled:
        ready, reason, probe_details = probe_platform_lifecycle(config)
        details["platform_lifecycle_probe"] = {
            "ready": ready,
            "reason": reason,
            **probe_details,
        }
        if not ready:
            details["platform_lifecycle_warning"] = reason

    if errors:
        reporter.record("preflight_failed", errors=errors, **details)
        raise RuntimeError("SDK E2E preflight failed:\n- " + "\n- ".join(errors))

    reporter.record("preflight_passed", **details)


def _check_template_ready(template_id: str, template: dict[str, Any], errors: list[str]) -> None:
    status = _first_present(
        template,
        "status",
        "state",
        "template_status",
        "templateStatus",
    )
    if status is None:
        return
    if str(status).lower() not in {"ready", "active", "available"}:
        errors.append(f"template {template_id!r} is not ready: status={status!r}")


def _first_present(data: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        if key in data:
            return data[key]
    return None


def _template_summary(template_id: str, template: dict[str, Any]) -> dict[str, Any]:
    return {
        "template_id": template_id,
        "name": _first_present(template, "name", "templateName", "template_name"),
        "status": _first_present(
            template,
            "status",
            "state",
            "template_status",
            "templateStatus",
        ),
        "response_keys": sorted(template),
    }
