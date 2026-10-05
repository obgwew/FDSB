# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/resolver_ops.py

import random

from . import runtime_state as _state
from .errors import FDSyntaxError
from .parse_utils import _process_escapes, _find_matching_bracket, _format_uptime


class ResolverMixin:

    def resolve(self, text: str) -> str:
        if not text:
            return text
        processed = _process_escapes(text)
        self._resolve_root_text = processed
        resolved = self._resolve_pass(processed, base_offset=0)
        if self._inline_call_values and '\uE000' in resolved:
            for sentinel, value in self._inline_call_values.items():
                if sentinel in resolved:
                    resolved = resolved.replace(sentinel, value)
        return resolved

    def resolve_sync(self, text: str) -> str:
        return self.resolve(text)

    def _resolve_pass(self, text: str, base_offset: int = 0) -> str:
        result: list[str] = []
        i = 0
        n = len(text)

        while i < n:
            if text[i] != '$':
                result.append(text[i])
                i += 1
                continue

            j = i + 1
            while j < n and (text[j].isalnum() or text[j] == '_'):
                j += 1

            cmd_name = text[i + 1:j]
            if not cmd_name:
                result.append('$')
                i += 1
                continue

            if j < n and text[j] == '[':
                bracket_end = _find_matching_bracket(text, j)
                if bracket_end == -1:
                    self._abort_with_error(
                        FDSyntaxError(f"Unclosed bracket in `${cmd_name}[`"),
                        base_offset + i
                    )
                inner_raw = text[j + 1:bracket_end]
                inner = self._resolve_pass(inner_raw, base_offset + j + 1)
                resolved = self._apply_cmd(cmd_name, inner, base_offset + i)
                result.append(resolved)
                i = bracket_end + 1
            else:
                val = self._resolve_bare(cmd_name)
                if val is not None:
                    result.append(val)
                    i = j
                elif cmd_name and (cmd_name[0].isalpha() or cmd_name[0] == '_'):
                    self._abort_with_error(
                        FDSyntaxError(f"Unknown Syntax : `${cmd_name}`"),
                        base_offset + i
                    )
                else:
                    result.append('$')
                    i += 1

        return ''.join(result)

    def _resolve_bare(self, cmd_name: str) -> str | None:
        import time as _time
        if cmd_name == 'messageID':
            return str(self.message.id)
        if cmd_name == 'message':
            full = self.message.content.strip()
            if getattr(self, 'is_event', False):
                return full
            parts = full.split(None, 1)
            return parts[1] if len(parts) > 1 else ""
        if cmd_name == 'randomUserID':
            guild = self.message.guild
            if guild:
                members = [m for m in guild.members if not m.bot]
                if members:
                    return str(random.choice(members).id)
            return ""
        if cmd_name == 'addTimestamp':
            return f'<t:{int(_time.time())}:T>'
        if cmd_name == 'uptime':
            if _state._BOT_START_TIME == 0.0:
                return ""
            return _format_uptime(_time.time() - _state._BOT_START_TIME)
        if cmd_name == 'ping':
            return f"{round(self.bot.latency * 1000)}ms"
        if cmd_name == 'return':
            return None
        if cmd_name in self.builtins:
            return str(self.builtins[cmd_name])
        
        if _state._inline_resolver is not None:
            val = _state._inline_resolver(cmd_name, [], self)
            if val is not None:
                return val
        return None
