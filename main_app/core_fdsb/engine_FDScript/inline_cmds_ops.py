# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/inline_cmds_ops.py

import random

from . import runtime_state as _state
from .definitions import KNOWN_COMMANDS
from .errors import FDLogicError, FDRuntimeError
from .parse_utils import _split_args, _truncate
from .storage_ops import _load_data, _load_ids_data


class InlineCmdsMixin:

    def _apply_cmd(self, cmd_name: str, inner: str, pos: int = 0) -> str:
        _ASYNC_ONLY_COMMANDS = ('httpGet', 'httpPost', 'httpPut', 'httpPatch', 'httpDelete')
        if cmd_name in _ASYNC_ONLY_COMMANDS:
            self._abort_with_error(
                FDLogicError(
                    f"`${cmd_name}` performs a network request and can only be used as its own "
                    f"standalone line (e.g. `${cmd_name}[...]` on its own line), not nested inside "
                    f"another command's arguments like `$description[...]`. Run it on its own line "
                    f"first, then read the result with `$httpResult[...]`."
                ),
                pos
            )

        if cmd_name == 'var':
            parts = _split_args(inner)
            if len(parts) == 1:
                return self.get_var(parts[0])
            if len(parts) == 2:
                self.set_var(parts[0], parts[1])
                self.log_event(f"var [{parts[0]}] ← {_truncate(parts[1])!r}")
                return ""
            self._abort_with_error(
                FDLogicError("`$var[...]` accepts 1 argument (read) or 2 arguments (write)"),
                pos
            )

        if cmd_name == 'return':
            key = inner.strip()
            if not key:
                self._abort_with_error(FDLogicError("`$return[]` — variable name cannot be empty"), pos)
            if key not in self.return_vars:
                self._abort_with_error(
                    FDRuntimeError(f"`$return[{key}]` — `{key}` has no value stored by any `$returnXxx` command"),
                    pos
                )
            return str(self.return_vars[key])

        math_result = self._apply_math_cmd(cmd_name, inner, pos)
        if math_result is not None:
            return math_result

        if cmd_name == 'randomint':
            parts = [x.strip() for x in inner.split(';')]
            if len(parts) == 2:
                a = int(float(parts[0])) if parts[0] else 0
                b = int(float(parts[1])) if parts[1] else 0
                return str(random.randint(min(a, b), max(a, b)))
            self._abort_with_error(FDLogicError("`$randomint` requires two arguments: `$randomint[min; max]`"), pos)
        if cmd_name == 'randomstr':
            parts = [p.strip() for p in inner.split(';') if p.strip()]
            return random.choice(parts) if parts else ""
        if cmd_name == 'getVar':
            parts = [x.strip() for x in inner.split(';')]
            if len(parts) == 2:
                name, user_id = parts
                if not name:
                    self._abort_with_error(FDLogicError("`$getVar[]` — variable name cannot be empty"), pos)
                if not user_id:
                    self._abort_with_error(FDLogicError("`$getVar[]` — user ID cannot be empty"), pos)
                data = _load_ids_data()
                return str(data.get(name, {}).get(user_id, ''))
            elif len(parts) == 1:
                key = parts[0]
                if not key:
                    self._abort_with_error(FDLogicError("`$getVar[]` — variable name cannot be empty"), pos)
                data = _load_data()
                return str(data.get(key, ''))
            else:
                self._abort_with_error(
                    FDLogicError(
                        "`$getVar[]` requires 1 or 2 arguments: `$getVar[name]` or `$getVar[name; user_id]`"
                    ),
                    pos
                )
        if _state._inline_resolver is not None:
            args = _split_args(inner) if inner.strip() else []
            val = _state._inline_resolver(cmd_name, args, self)
            if val is not None:
                return val
        if cmd_name in KNOWN_COMMANDS:
            self._abort_with_error(
                FDLogicError(
                    f"`${cmd_name}` cannot be used as an inline expression inside another command's arguments"
                ),
                pos
            )
        self._abort_with_error(
            FDLogicError(f"Unknown command: `${cmd_name}`"),
            pos
        )
