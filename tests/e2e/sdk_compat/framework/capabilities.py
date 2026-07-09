# Copyright (c) 2026 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

LIFECYCLE = "lifecycle"
COMMANDS = "commands"
FILESYSTEM = "filesystem"
RUN_CODE = "run_code"
PAUSE_RESUME = "pause_resume"
NETWORK_POLICY = "network_policy"
PROXY_URL = "proxy_url"

COMMON_CAPABILITIES = frozenset({LIFECYCLE, COMMANDS, FILESYSTEM, RUN_CODE})

E2B_CAPABILITIES = COMMON_CAPABILITIES

CUBESANDBOX_CAPABILITIES = frozenset(
    {
        *COMMON_CAPABILITIES,
        PAUSE_RESUME,
        NETWORK_POLICY,
        PROXY_URL,
    }
)
