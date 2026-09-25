# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/functions_ops.py

_CALL_HEAD = '$call['
_CALL_SENTINEL = '\uE000{}\uE001'


def _find_inline_call_spans(text: str) -> list:
    spans = []
    i = 0
    while True:
        start = text.find(_CALL_HEAD, i)
        if start < 0:
            return spans
        p = start + len(_CALL_HEAD)
        depth = 1
        end = -1
        while p < len(text):
            c = text[p]
            if c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0:
                    end = p
                    break
            p += 1
        if end < 0:
            return spans
        spans.append((start, end))
        i = end + 1


class FunctionsMixin:
    async def _run_block_slice(self, tokens: list, start: int, end: int, ctx) -> None:
        slice_tokens = tokens[start:end]
        await self._execute(slice_tokens, ctx, start=0)

    def _collect_functions(self, tokens: list) -> dict:
        functions: dict = {}
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if not isinstance(tok, str) and getattr(tok, 'name', None) == "func":
                name = tok.args[0].strip() if tok.args else ""
                end = self._find_closer(tokens, i + 1, "func", "endfunc")
                if name:
                    functions[name] = (i + 1, end)
                i = end + 1
                continue
            i += 1
        return functions

    async def _exec_call(self, cmd, tokens: list, ctx) -> None:
        from FDCore import FDLogicError, FDRuntimeError, _send_error

        ctx.set_line(cmd.line_no)
        dest = await ctx.get_dest()

        if not cmd.args:
            await _send_error(dest, FDLogicError("`$call[]` — function name cannot be empty"))
            return

        raw_name = cmd.args[0]
        name = (ctx.resolve(raw_name)).strip() if raw_name else ""

        if not name:
            await _send_error(dest, FDLogicError("`$call[]` — function name cannot be empty"))
            return

        body = self.functions.get(name)
        if body is None:
            await _send_error(dest, FDRuntimeError(
                f"`$call[{name}]` — no function named `{name}` is defined "
                f"(define it with `$func[{name}] ... $endfunc`)"
            ))
            return

        depth = getattr(ctx, '_call_depth', 0)
        if depth >= self._MAX_CALL_DEPTH:
            await _send_error(dest, FDRuntimeError(
                f"`$call[{name}]` — maximum function call depth "
                f"({self._MAX_CALL_DEPTH}) exceeded; likely infinite recursion"
            ))
            return

        body_start, body_end = body
        ctx._call_depth = depth + 1
        ctx.log_event(f"call [{name}] → entering function")
        try:
            await self._run_block_slice(tokens, body_start, body_end, ctx)
        finally:
            ctx._call_depth = depth
        ctx.log_event(f"call [{name}] → exiting function")

    async def _run_function_capture(self, name: str, tokens: list, ctx) -> str:
        from FDCore import FDLogicError, FDRuntimeError, _send_error, _truncate

        dest = await ctx.get_dest()

        if not name:
            await _send_error(dest, FDLogicError("`$call[]` — function name cannot be empty"))
            return ""

        body = self.functions.get(name)
        if body is None:
            await _send_error(dest, FDRuntimeError(
                f"`$call[{name}]` — no function named `{name}` is defined "
                f"(define it with `$func[{name}] ... $endfunc`)"
            ))
            return ""

        depth = getattr(ctx, '_call_depth', 0)
        if depth >= self._MAX_CALL_DEPTH:
            await _send_error(dest, FDRuntimeError(
                f"`$call[{name}]` — maximum function call depth "
                f"({self._MAX_CALL_DEPTH}) exceeded; likely infinite recursion"
            ))
            return ""

        body_start, body_end = body
        prev_capture = getattr(ctx, '_capture_out', None)
        ctx._capture_out = []
        ctx._call_depth = depth + 1
        try:
            await self._run_block_slice(tokens, body_start, body_end, ctx)
            captured = '\n'.join(ctx._capture_out).strip()
        finally:
            ctx._call_depth = depth
            ctx._capture_out = prev_capture

        ctx.log_event(f"call [{name}] → captured {_truncate(captured)!r}")
        return captured

    async def _expand_inline_calls(self, args: list, tokens, ctx) -> None:
        if not args:
            return

        for idx, arg in enumerate(args):
            if not arg or '$call[' not in arg:
                continue

            spans = _find_inline_call_spans(arg)
            if not spans:
                continue

            parts = []
            last = 0
            for start, end in spans:
                parts.append(arg[last:start])
                raw_name = arg[start + len(_CALL_HEAD):end]
                name = (ctx.resolve(raw_name)).strip() if raw_name else ""

                value = await self._run_function_capture(
                    name,
                    tokens if tokens is not None else self._active_tokens,
                    ctx,
                )

                sentinel = _CALL_SENTINEL.format(len(ctx._inline_call_values))
                ctx._inline_call_values[sentinel] = value
                parts.append(sentinel)
                last = end + 1

            parts.append(arg[last:])
            args[idx] = ''.join(parts)