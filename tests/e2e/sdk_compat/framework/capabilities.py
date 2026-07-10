# Copyright (c) 2026 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

LIFECYCLE = "lifecycle"
COMMANDS = "commands"
FILESYSTEM = "filesystem"
RUN_CODE = "run_code"
PAUSE_RESUME = "pause_resume"
NETWORK_ALLOW_DENY = "network_allow_deny"
NETWORK_PUBLIC_ACCESS = "network_public_access"
NETWORK_L7_RULES = "network_l7_rules"
PROXY_URL = "proxy_url"

COMMON_CAPABILITIES = frozenset({LIFECYCLE, COMMANDS, FILESYSTEM, RUN_CODE})

E2B_CAPABILITIES = frozenset(
    {
        *COMMON_CAPABILITIES,
        PAUSE_RESUME,
        NETWORK_ALLOW_DENY,
        NETWORK_PUBLIC_ACCESS,
    }
)

CUBESANDBOX_CAPABILITIES = frozenset(
    {
        *COMMON_CAPABILITIES,
        PAUSE_RESUME,
        NETWORK_ALLOW_DENY,
        NETWORK_PUBLIC_ACCESS,
        NETWORK_L7_RULES,
        PROXY_URL,
    }
)
