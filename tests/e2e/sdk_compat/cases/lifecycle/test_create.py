# Copyright (c) 2026 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from framework.assertions import assert_command_ok

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.sdk_compat,
    pytest.mark.lifecycle,
    pytest.mark.p0,
]


@pytest.mark.smoke
def test_create_returns_usable_sandbox(sdk_sandbox, sdk_e2e_config):
    info = sdk_sandbox.info()

    assert sdk_sandbox.sandbox_id
    assert info.sandbox_id == sdk_sandbox.sandbox_id

    result = sdk_sandbox.run_command(
        "printf 'sdk-compat:%s' \"$USER\"",
        timeout=sdk_e2e_config.command_timeout,
    )
    assert_command_ok(result)
    assert result.stdout.startswith("sdk-compat:")


def test_info_is_stable_for_created_sandbox(sdk_sandbox):
    first = sdk_sandbox.info()
    second = sdk_sandbox.info()

    assert first.sandbox_id == sdk_sandbox.sandbox_id
    assert second.sandbox_id == sdk_sandbox.sandbox_id
