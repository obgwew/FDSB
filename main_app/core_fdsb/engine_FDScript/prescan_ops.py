# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/prescan_ops.py

import re

from .parse_utils import _find_matching_bracket, _strip_inline_comment

def _scan_suppress_errors(script_text: str) -> tuple[bool, str | None]:
    match = re.search(r'\$suppressErrors\b', script_text)
    if not match:
        return False, None

    end = match.end()
    if end < len(script_text) and script_text[end] == '[':
        close = _find_matching_bracket(script_text, end)
        if close != -1:
            custom = script_text[end + 1:close].strip()
            return True, (custom or None)

    return True, None

_REMOVE_LINKS_RE = re.compile(r'\$removeLinks(?![A-Za-z0-9_])')

def _scan_flag(script_text: str, pattern: 're.Pattern') -> bool:
    for line in script_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if pattern.search(_strip_inline_comment(stripped)):
            return True
    return False

def _scan_remove_links(script_text: str) -> bool:
    return _scan_flag(script_text, _REMOVE_LINKS_RE)

_EPHEMERAL_RE = re.compile(r'\$ephemeral(?![A-Za-z0-9_])')

def _scan_ephemeral(script_text: str) -> bool:
    return _scan_flag(script_text, _EPHEMERAL_RE)

script_wants_ephemeral = _scan_ephemeral
