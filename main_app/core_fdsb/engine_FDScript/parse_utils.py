# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/parse_utils.py

import re
import time

from .errors import _FDError, FDLogicError

def _find_matching_bracket(text: str, open_pos: int) -> int:
    depth = 0
    i = open_pos
    while i < len(text):
        if text[i] == '[':
            depth += 1
        elif text[i] == ']':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1

def _check_brackets(text: str) -> tuple[bool, str]:
    depth = 0
    for pos, ch in enumerate(text):
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth < 0:
                return False, f"Extra closing `]` at position {pos}"
    if depth > 0:
        return False, f"{'One unclosed' if depth == 1 else f'{depth} unclosed'} opening `[`"
    return True, ""

_ESCAPE_MAP: dict[str, str] = {
    'n':  '\n',
    't':  '\t',
    'r':  '\r',
    '\\': '\\',
    '0':  '\0',
    'a':  '\a',
    'b':  '\b',
    'f':  '\f',
    'v':  '\v',
    "'":  "'",
    '"':  '"',
}

def _process_escapes(text: str) -> str:
    def _replace(m: 're.Match') -> str:
        ch = m.group(1)
        return _ESCAPE_MAP.get(ch, m.group(0))
    return re.sub(r'\\(.)', _replace, text)

_VALID_TIMESTAMP_FORMATS = {'t', 'T', 'd', 'D', 'f', 'F', 'R'}

def _build_timestamp(fmt: str) -> str | _FDError:
    fmt = fmt.strip() if fmt.strip() else 'T'
    if fmt not in _VALID_TIMESTAMP_FORMATS:
        return FDLogicError(
            f"`$addTimestamp` — invalid format `{fmt}`.\n"
            f"Valid formats: `t` `T` `d` `D` `f` `F` `R`"
        )
    return f'<t:{int(time.time())}:{fmt}>'

_REACTIONS_MAX: int = 20

_CLEAR_DEFAULT: int = 10

_CLEAR_MAX:     int = 100

def _parse_reaction_emoji(raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    if re.match(r'^<a?:[a-zA-Z0-9_]+:\d+>$', raw):
        return raw
    return raw

def _extract_all_emojis(text: str) -> list[str]:
    custom_emoji_pattern = r'<a?:[a-zA-Z0-9_]+:\d+>'
    emoji_range = (
        r'[\U0001F300-\U0001F5FF'
        r'\U0001F600-\U0001F64F'
        r'\U0001F680-\U0001F6FF'
        r'\U0001F900-\U0001F9FF'
        r'\U0001FA70-\U0001FAFF'
        r'\u2600-\u26FF'
        r'\u2700-\u27BF]'
    )
    single_emoji = f'(?:{emoji_range}|[\U0001F1E6-\U0001F1FF]{{2}}|[0-9#*]\ufe0f?\u20e3)'
    modifier  = r'[\U0001F3FB-\U0001F3FF]?'
    selector  = r'\ufe0f?'
    component = f'{single_emoji}{modifier}{selector}'
    unicode_emoji_pattern = f'{component}(?:\u200d{component})*'
    combined_pattern = f'({custom_emoji_pattern}|{unicode_emoji_pattern})'
    return re.findall(combined_pattern, text)

_LOG_CHAR_LIMIT = 2000

_LOG_FILE_LIMIT = 10 * 1024 * 1024

def _truncate(text: str, limit: int = 40) -> str:
    text = text.replace('\n', ' ')
    return text[:limit] + '…' if len(text) > limit else text

def _format_uptime(seconds: float) -> str:
    total = int(seconds)
    days,    total   = divmod(total, 86400)
    hours,   total   = divmod(total, 3600)
    minutes, secs    = divmod(total, 60)
    parts = []
    if days:    parts.append(f"{days}d")
    if hours:   parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return ' '.join(parts)

_NAMED_COLORS: dict[str, int] = {
    "red":0xE74C3C, "green":0x2ECC71, "blue":0x3498DB, "yellow":0xF1C40F,
    "orange":0xE67E22, "purple":0x9B59B6, "pink":0xFF69B4, "white":0xFFFFFF,
    "black":0x000000, "gray":0x95A5A6, "grey":0x95A5A6, "cyan":0x1ABC9C,
    "gold":0xF9A825, "navy":0x2C3E50, "lime":0x27AE60, "brown":0xA0522D,
    "teal":0x008080, "magenta":0xFF00FF, "blurple":0x5865F2, "dark":0x2B2D31,
}

def _parse_color(raw: str) -> int:
    raw = raw.strip().lower()
    if raw in _NAMED_COLORS:
        return _NAMED_COLORS[raw]
    try:
        return int(raw.lstrip("#"), 16)
    except ValueError:
        return 0x2B2D31

_NAMED_SEPARATORS: dict[str, str] = {
    "dot": ".", "com": ",", "apo": "'", "sem": ";", "colon": ":",
}

def _parse_separator(raw: str) -> str:
    return _NAMED_SEPARATORS.get(raw.strip(), raw.strip())

def _strip_inline_comment(line: str) -> str:
    depth = 0
    for i, ch in enumerate(line):
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
        elif ch == '#' and depth == 0:
            return line[:i].rstrip()
    return line

def _split_args(inner: str) -> list[str]:
    if not inner:
        return []
    args = []
    depth = 0
    current = []
    saw_delim = False
    for ch in inner:
        if ch == "[":
            depth += 1
            current.append(ch)
        elif ch == "]":
            depth -= 1
            current.append(ch)
        elif ch == ";" and depth == 0:
            args.append("".join(current).strip())
            current = []
            saw_delim = True
        else:
            current.append(ch)
    if current or saw_delim:
        args.append("".join(current).strip())
    return args
