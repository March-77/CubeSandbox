# Copyright (c) 2026 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os

import pytest

from framework.assertions import assert_command_ok
from framework.capabilities import NETWORK_ALLOW_DENY, NETWORK_PUBLIC_ACCESS

TCP_TARGET_IP = os.environ.get("SDK_E2E_TCP_TARGET_IP", "8.8.8.8")
TCP_TARGET_PORT = int(os.environ.get("SDK_E2E_TCP_TARGET_PORT", "53"))

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.sdk_compat,
    pytest.mark.p1,
    pytest.mark.requires_internet,
]


def _tcp_probe_command(host: str = TCP_TARGET_IP, port: int = TCP_TARGET_PORT) -> str:
    return (
        "python3 - <<'PY'\n"
        "import socket\n"
        "s = socket.socket()\n"
        "s.settimeout(5)\n"
        f"rc = s.connect_ex(({host!r}, {port}))\n"
        "print('OK' if rc == 0 else f'FAIL:{rc}')\n"
        "s.close()\n"
        "PY"
    )


@pytest.mark.requires_capability(NETWORK_ALLOW_DENY)
@pytest.mark.sandbox_create_options(
    network={
        "allow_out": [TCP_TARGET_IP],
        "deny_out": ["0.0.0.0/0"],
    },
)
def test_allow_out_can_punch_through_deny_all(sdk_sandbox, sdk_e2e_config):
    result = sdk_sandbox.run_command(
        _tcp_probe_command(),
        timeout=sdk_e2e_config.command_timeout,
    )

    assert_command_ok(result)
    assert result.stdout.strip() == "OK", (
        f"allow_out did not permit {TCP_TARGET_IP}:{TCP_TARGET_PORT}; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


@pytest.mark.requires_capability(NETWORK_ALLOW_DENY)
@pytest.mark.sandbox_create_options(
    network={
        "deny_out": ["0.0.0.0/0"],
    },
)
def test_deny_out_blocks_public_tcp(sdk_sandbox, sdk_e2e_config):
    result = sdk_sandbox.run_command(
        _tcp_probe_command(),
        timeout=sdk_e2e_config.command_timeout,
    )

    assert_command_ok(result)
    assert result.stdout.strip() != "OK", (
        f"deny_out did not block {TCP_TARGET_IP}:{TCP_TARGET_PORT}; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


@pytest.mark.requires_capability(NETWORK_PUBLIC_ACCESS)
@pytest.mark.sandbox_create_options(allow_internet_access=False)
def test_allow_internet_access_false_blocks_public_tcp(sdk_sandbox, sdk_e2e_config):
    result = sdk_sandbox.run_command(
        _tcp_probe_command(),
        timeout=sdk_e2e_config.command_timeout,
    )

    assert_command_ok(result)
    assert result.stdout.strip() != "OK", (
        "allow_internet_access=False did not block public TCP egress; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
