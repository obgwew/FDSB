# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/tokenizer.py

from .definitions import KNOWN_COMMANDS
from .parse_utils import (
    _check_brackets, _find_matching_bracket, _split_args, _strip_inline_comment,
)

_cmd_loader = None

def register_command_loader(fn) -> None:
    global _cmd_loader
    _cmd_loader = fn

class Command:
    def __init__(self, name: str, args: list[str], raw: str, line_no: int | None = None):
        self.name = name
        self.args = args
        self.raw  = raw
        self.line_no = line_no

class TextToken(str):
    def __new__(cls, value: str, line_no: int | None = None):
        obj = str.__new__(cls, value)
        obj.line_no = line_no
        return obj

def tokenise(line: str) -> 'Command | str | None':
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    line = _strip_inline_comment(line)
    if not line:
        return None
    if not line.startswith("$"):
        return line

    body = line[1:]
    if body in {"else", "endif", "endwhile", "endfor", "endfunc", "break"}:
        return Command(body, [], line)

    bracket_pos = body.find("[")
    if bracket_pos == -1:
        name = body
        if name not in KNOWN_COMMANDS:
            return Command("__unknown__", [name], line)
        return Command(name, [], line)

    name = body[:bracket_pos].strip()
    if name not in KNOWN_COMMANDS:
        return Command("__unknown__", [name], line)

    rest = body[bracket_pos:]
    valid, err_msg = _check_brackets(rest)
    if not valid:
        raise SyntaxError(f"Bracket error in `{name}`: {err_msg}")

    inner = rest[1:-1]
    args  = _split_args(inner)
    return Command(name, args, line)

_CORE_INLINE_NO_ARGS: set[str] = {
    'message', 'messageID', 'ping', 'uptime', 'mention', 'return',
    'authorID', 'authorName', 'botID', 'botName',
    'channelID', 'channelName', 'guildID', 'guildName',
    'randomUserID', 'customID', 'boostLevel', 'guildVerificationLvl',
    'addTimestamp',
}

_CORE_INLINE_WITH_ARGS: set[str] = {
    'message', 'var', 'return', 'getVar',
    'randomint', 'randomstr',
    'sum', 'sub', 'mul', 'div', 'mod',
    "checkContains",
    'floor', 'ceil', 'power',
}

def _is_inline_capable(cmd_name: str, has_args: bool) -> bool:
    core_set = _CORE_INLINE_WITH_ARGS if has_args else _CORE_INLINE_NO_ARGS
    if cmd_name in core_set:
        return True
    if _cmd_loader is None:
        return False
    module = _cmd_loader(cmd_name)
    return module is not None and hasattr(module, 'resolve_inline')

def tokenise_line(line: str, base_line_no: int = 1) -> list:
    line = line.strip()
    if not line or line.startswith('#'):
        return []
    line = _strip_inline_comment(line)
    if not line:
        return []

    def _line_at(pos: int) -> int:
        return base_line_no + line.count('\n', 0, pos)

    tokens:     list      = []
    text_buf:   list[str] = []
    text_start: int       = 0
    i            = 0
    n            = len(line)
    at_boundary  = True

    def flush_text() -> None:
        nonlocal text_buf, text_start
        chunk = ''.join(text_buf).strip()
        if chunk:
            tokens.append(TextToken(chunk, _line_at(text_start)))
        text_buf = []

    while i < n:
        ch = line[i]

        if ch in (' ', '\t'):
            if not text_buf:
                text_start = i
            text_buf.append(ch)
            at_boundary = True
            i += 1
            continue

        if ch == '$' and at_boundary:
            j = i + 1
            while j < n and (line[j].isalnum() or line[j] == '_'):
                j += 1
            cmd_name = line[i + 1:j]

            is_control = cmd_name in {'else', 'endif', 'endwhile', 'endfor', 'break'}
            is_known   = cmd_name in KNOWN_COMMANDS or is_control

            if cmd_name and is_known:
                if j >= n or line[j] != '[':
                    if _is_inline_capable(cmd_name, has_args=False):
                        if not text_buf:
                            text_start = i
                        text_buf.append(f'${cmd_name}')
                        i = j
                        at_boundary = False
                        continue
                    flush_text()
                    tokens.append(Command(cmd_name, [], f'${cmd_name}', _line_at(i)))
                    i = j
                    at_boundary = True
                    continue

                bracket_end = _find_matching_bracket(line, j)
                if bracket_end == -1:
                    flush_text()
                    tokens.append(Command(
                        '__syntax_error__',
                        [f'Unclosed bracket in `${cmd_name}`'],
                        f'${cmd_name}[',
                        _line_at(i)
                    ))
                    i = j + 1
                    at_boundary = False
                    continue

                inner = line[j + 1:bracket_end]
                ok, err_msg = _check_brackets(f'[{inner}]')
                if not ok:
                    flush_text()
                    tokens.append(Command(
                        '__syntax_error__',
                        [f'Bracket error in `{cmd_name}`: {err_msg}'],
                        line,
                        _line_at(i)
                    ))
                    i = bracket_end + 1
                    at_boundary = True
                    continue

                if _is_inline_capable(cmd_name, has_args=True):
                    if not text_buf:
                        text_start = i
                    text_buf.append(f'${cmd_name}[{inner}]')
                    i = bracket_end + 1
                    at_boundary = False
                    continue

                flush_text()
                tokens.append(Command(cmd_name, _split_args(inner), f'${cmd_name}[{inner}]', _line_at(i)))
                i = bracket_end + 1
                at_boundary = True
                continue

            if cmd_name and not is_known:
                flush_text()
                tokens.append(Command('__unknown__', [cmd_name], f'${cmd_name}', _line_at(i)))
                i = j
                at_boundary = True
                continue

        if not text_buf:
            text_start = i
        text_buf.append(ch)
        at_boundary = False
        i += 1

    flush_text()
    return tokens
