# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/control_flow.py

class ControlFlowMixin:

    # ── if / elif / else / endif ──────────────────────────────
    async def _exec_if(self, tokens: list, start: int, ctx) -> int:
        i, branch_taken = start, False

        while i < len(tokens):
            tok = tokens[i]
            if tok.name in ("if", "elif"):
                ctx.set_line(tok.line_no)
                cond_args = list(tok.args)
                await self._expand_inline_calls(cond_args, tokens, ctx)
                cond_str = cond_args[0] if cond_args else ""
                cond_val = self._evaluate(cond_str, ctx)
                ctx.log_event(f"{tok.name} [{cond_str}] → {'✓' if cond_val else '✗'}")
                i += 1
                execute = not branch_taken and cond_val
                if execute:
                    branch_taken = True
                i = await self._run_block_until(tokens, i, {"elif", "else", "endif"}, ctx, execute=execute)
                if i == "break":
                    return "break"
                continue

            if tok.name == "else":
                ctx.log_event(f"else → {'taken' if not branch_taken else 'skipped'}")
                i += 1
                i = await self._run_block_until(tokens, i, {"endif"}, ctx, execute=not branch_taken)
                if i == "break":
                    return "break"
                continue

            if tok.name == "endif":
                return i + 1
            i += 1
        return i

    # ── while / endwhile ──────────────────────────────────────
    async def _exec_while(self, tokens: list, start: int, ctx) -> int:
        tok = tokens[start]
        body_start, body_end = start + 1, self._find_closer(tokens, start + 1, "while", "endwhile")
        iterations = 0
        while True:
            ctx.set_line(tok.line_no)
            cond_args = list(tok.args)
            await self._expand_inline_calls(cond_args, tokens, ctx)
            cond_str = cond_args[0] if cond_args else ""
            if not self._evaluate(cond_str, ctx):
                break
            iterations += 1
            if await self._run_block_slice(tokens, body_start, body_end, ctx) == "break":
                break
        ctx.log_event(f"while → {iterations} iters")
        return body_end + 1

    # ── for / endfor ──────────────────────────────────────────
    async def _exec_for(self, tokens: list, start: int, ctx) -> int:
        from FDCore import FDRuntimeError, _send_error

        tok = tokens[start]
        ctx.set_line(tok.line_no)
        count_args = list(tok.args)
        await self._expand_inline_calls(count_args, tokens, ctx)
        count_str = (ctx.resolve(count_args[0])) if count_args else "0"
        try:
            count = int(count_str)
        except ValueError:
            loc = f"Line {tok.line_no}: " if tok.line_no is not None else ""
            await _send_error(ctx.message.channel, FDRuntimeError(f"{loc}`$for` expects integer, got: `{count_str}`"))
            count = 0
        body_start, body_end = start + 1, self._find_closer(tokens, start + 1, "for", "endfor")
        for _ in range(count):
            if await self._run_block_slice(tokens, body_start, body_end, ctx) == "break":
                break
        ctx.log_event(f"for [{count}] → {count} iters")
        return body_end + 1

    # ── shared block runners (used by if/while/for AND by $call) ──
    async def _run_block_until(self, tokens, start, stoppers, ctx, execute):
        i, depth = start, 0
        while i < len(tokens):
            tok = tokens[i]

            if not isinstance(tok, str):
                if depth > 0:
                    if tok.name in ("if", "while", "for"):
                        depth += 1
                    elif tok.name in ("endif", "endwhile", "endfor"):
                        depth -= 1
                    i += 1
                    continue

                if tok.name in stoppers:
                    return i

                if not execute:
                    if tok.name in ("if", "while", "for"):
                        depth = 1
                    i += 1
                    continue

                if tok.name == "break":
                    return "break"
                if tok.name == "if":
                    i = await self._exec_if(tokens, i, ctx)
                    if i == "break":
                        return "break"
                    continue
                if tok.name == "while":
                    i = await self._exec_while(tokens, i, ctx)
                    continue
                if tok.name == "for":
                    i = await self._exec_for(tokens, i, ctx)
                    continue
                if tok.name == "func":
                    i = self._find_closer(tokens, i + 1, "func", "endfunc") + 1
                    continue
                if tok.name == "endfunc":
                    i += 1
                    continue
                if tok.name == "call":
                    await self._exec_call(tok, tokens, ctx)
                    i += 1
                    continue

                i = await self._exec_command_with_lookahead(tok, tokens, i + 1, ctx)
                continue

            if execute and depth == 0:
                i = await self._process_text_token(tokens, tok, i + 1, ctx)
            else:
                i += 1
        return i

    async def _run_block_slice(self, tokens, start, end, ctx):
        i = start
        while i < end:
            tok = tokens[i]
            i += 1
            if isinstance(tok, str):
                i = await self._process_text_token(tokens, tok, i, ctx)
                continue

            if tok.name == "break":
                return "break"
            if tok.name == "if":
                res = await self._exec_if(tokens, i - 1, ctx)
                if res == "break":
                    return "break"
                i = res
            elif tok.name == "while":
                i = await self._exec_while(tokens, i - 1, ctx)
            elif tok.name == "for":
                i = await self._exec_for(tokens, i - 1, ctx)
            elif tok.name == "func":
                i = self._find_closer(tokens, i, "func", "endfunc") + 1
            elif tok.name == "endfunc":
                pass
            elif tok.name == "call":
                await self._exec_call(tok, tokens, ctx)
            else:
                i = await self._exec_command_with_lookahead(tok, tokens, i, ctx)
        return None

    def _find_closer(self, tokens, start, opener, closer):
        depth, i = 0, start
        while i < len(tokens):
            tok = tokens[i]
            if not isinstance(tok, str):
                if tok.name == opener:
                    depth += 1
                elif tok.name == closer:
                    if depth == 0:
                        return i
                    depth -= 1
            i += 1
        return i