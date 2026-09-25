# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/math_ops.py

import math


class MathOpsMixin:

    _MATH_BASIC_OPS = ('sum', 'sub', 'mul', 'div', 'mod')
    _MATH_ROUNDING_OPS = ('floor', 'ceil')

    def _apply_math_cmd(self, cmd_name: str, inner: str, pos: int = 0):
        """Entry point called from ExecutionContext._apply_cmd.

        Returns the resolved string if `cmd_name` is a math command,
        or None if it isn't (caller should keep checking other command
        families)."""
        if cmd_name in self._MATH_BASIC_OPS:
            return self._math_basic(cmd_name, inner, pos)
        if cmd_name in self._MATH_ROUNDING_OPS:
            return self._math_rounding(cmd_name, inner, pos)
        if cmd_name == 'power':
            return self._math_power(inner, pos)
        return None

    def _math_basic(self, cmd_name: str, inner: str, pos: int) -> str:
        from FDCore import _split_args, FDLogicError, FDRuntimeError

        parts = _split_args(inner)
        if len(parts) < 2:
            self._abort_with_error(
                FDLogicError(f"`${cmd_name}` requires at least 2 arguments (e.g. `${cmd_name}[1; 2; 3]`)"),
                pos
            )

        try:
            values = [float(p) if p else 0.0 for p in parts]
        except ValueError:
            self._abort_with_error(
                FDLogicError(
                    f"`${cmd_name}` — Non-numeric value. Cannot perform math operations on text, "
                    f"ensure you are using numbers."
                ),
                pos
            )

        if cmd_name == 'sum':
            res = sum(values)
        elif cmd_name == 'mul':
            res = 1.0
            for v in values:
                res *= v
        elif cmd_name == 'sub':
            res = values[0]
            for v in values[1:]:
                res -= v
        elif cmd_name == 'div':
            res = values[0]
            for v in values[1:]:
                if v == 0:
                    self._abort_with_error(FDRuntimeError("Division by zero in math operation"), pos)
                res /= v
        else:  # mod
            res = values[0]
            for v in values[1:]:
                if v == 0:
                    self._abort_with_error(FDRuntimeError("Division by zero in math operation (mod)"), pos)
                res %= v

        return str(int(res)) if float(res).is_integer() else str(res)

    def _math_rounding(self, cmd_name: str, inner: str, pos: int) -> str:
        from FDCore import _split_args, FDLogicError

        parts = _split_args(inner)
        if len(parts) != 1:
            self._abort_with_error(
                FDLogicError(f"`${cmd_name}` requires exactly 1 argument (e.g. `${cmd_name}[3.7]`)"),
                pos
            )

        try:
            value = float(parts[0]) if parts[0] else 0.0
        except ValueError:
            self._abort_with_error(
                FDLogicError(
                    f"`${cmd_name}` — Non-numeric value. Cannot perform math operations on text, "
                    f"ensure you are using numbers."
                ),
                pos
            )

        res = math.floor(value) if cmd_name == 'floor' else math.ceil(value)
        return str(res)

    def _math_power(self, inner: str, pos: int) -> str:
        from FDCore import _split_args, FDLogicError, FDRuntimeError

        parts = _split_args(inner)
        if len(parts) != 2:
            self._abort_with_error(
                FDLogicError("`$power` requires exactly 2 arguments: `$power[base; exponent]`"),
                pos
            )

        try:
            base = float(parts[0]) if parts[0] else 0.0
            exponent = float(parts[1]) if parts[1] else 0.0
        except ValueError:
            self._abort_with_error(
                FDLogicError(
                    "`$power` — Non-numeric value. Cannot perform math operations on text, "
                    "ensure you are using numbers."
                ),
                pos
            )

        try:
            res = base ** exponent
        except (OverflowError, ZeroDivisionError):
            self._abort_with_error(
                FDRuntimeError("`$power` — result is too large or mathematically undefined"),
                pos
            )

        if isinstance(res, complex):
            self._abort_with_error(
                FDRuntimeError(
                    "`$power` — result is a complex number (negative base with fractional exponent)"
                ),
                pos
            )

        return str(int(res)) if float(res).is_integer() else str(res)