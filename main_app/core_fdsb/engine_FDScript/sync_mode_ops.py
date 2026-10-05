# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/sync_mode_ops.py

from .errors import FDAbortScript
from .tokenizer import Command


import asyncio


class SyncModeMixin:
    _SYNC_CLOSERS  = ("endif", "elif", "else", "endwhile", "endfor", "break")
    _SYNC_GUARDS   = ("onlyAdmin", "onlyIf")
    _SYNC_BARRIERS = ("useChannel", "suppressErrors", "syncMode")

    async def _exec_sync_mode(self, cmd, ctx) -> None:
        ctx.log_event("syncMode → (no commands below it in this block)")

    async def _exec_sync_block(self, tokens: list, start: int, ctx) -> int:

        ctx.log_event("syncMode → commands below run together as one batch")

        steps: list[tuple[int, int]] = []  

        async def flush():
            nonlocal steps
            batch, steps = steps, []
            await self._sync_run_batch(tokens, batch, ctx)

        i = start
        n = len(tokens)
        while i < n:
            tok = tokens[i]

            if isinstance(tok, str):
                end = self._sync_step_end(tokens, i)
                steps.append((i, end))
                i = end
                continue

            name = tok.name

            if name in self._SYNC_CLOSERS:
                break

            if name in self._SYNC_GUARDS:
                i = await self._exec_command_with_lookahead(tok, tokens, i + 1, ctx)
                continue

            if name in ("if", "while", "for"):
                await flush()
                handler = {"if": self._exec_if, "while": self._exec_while, "for": self._exec_for}[name]
                i = await handler(tokens, i, ctx)
                continue

            if name == "func":
                i = self._find_closer(tokens, i + 1, "func", "endfunc") + 1
                continue
            if name == "endfunc":
                i += 1
                continue
            if name == "call":
                await flush()
                await self._exec_call(tok, tokens, ctx)
                i += 1
                continue

            if name in self._SYNC_BARRIERS:
                await flush()
                i = await self._exec_command_with_lookahead(tok, tokens, i + 1, ctx)
                continue

            end = self._sync_step_end(tokens, i)
            steps.append((i, end))
            i = end

        await flush()
        return i

    def _sync_step_end(self, tokens: list, i: int) -> int:

        head = tokens[i]
        end = i + 1

        if isinstance(head, str):
            follow = "addButton"
        elif head.name in self._SEND_COMMANDS or head.name == "addButton":
            follow = "addButton"
        elif head.name == "editButton":
            follow = "editButton"
        else:
            return end

        j = end
        got_wait = False
        while j < len(tokens):
            t = tokens[j]
            if isinstance(t, str):
                if not t.strip():
                    j += 1
                    continue
                break
            if isinstance(t, Command):
                if t.name == follow:
                    end = j + 1
                    j += 1
                    continue
                if t.name == "wait" and not got_wait:
                    got_wait = True
                    end = j + 1
                    break
            break
        return end

    async def _sync_run_step(self, tokens: list, head: int, end: int, ctx, serialize_view: bool = False) -> None:
        tok = tokens[head]
        uses_view = serialize_view and (
            isinstance(tok, str)
            or tok.name in self._SEND_COMMANDS
            or tok.name in ("addButton", "editButton")
        )

        async def _go():
            if isinstance(tok, str):
                await self._process_text_token(tokens, tok, head + 1, ctx)
            else:
                await self._exec_command_with_lookahead(tok, tokens, head + 1, ctx)

        if uses_view:
            lock = getattr(ctx, "_sync_view_lock", None)
            if lock is None:
                lock = ctx._sync_view_lock = asyncio.Lock()
            async with lock:
                await _go()
        else:
            await _go()

    async def _sync_guard(self, tokens, head, end, ctx, serialize_view=False) -> None:
        try:
            await self._sync_run_step(tokens, head, end, ctx, serialize_view)
        except (FDAbortScript, asyncio.CancelledError):
            raise
        except Exception as e:
            ctx.log_event(f"warning: syncMode step failed: {e}")

    async def _sync_run_batch(self, tokens: list, steps: list, ctx) -> None:

        if not steps:
            return

        ctx.log_event(f"syncMode → launching {len(steps)} step(s) together")
        serialize_view = any(
            isinstance(t, Command) and t.name in ("addButton", "editButton")
            for h, e in steps for t in tokens[h:e]
        )
        tasks = [asyncio.create_task(self._sync_guard(tokens, h, e, ctx, serialize_view)) for h, e in steps]

        try:
            _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        except asyncio.CancelledError:
            for t in tasks:
                t.cancel()
            raise

        if pending:
            for t in pending:
                t.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

        abort = None
        for t in tasks:
            if t.cancelled():
                continue
            exc = t.exception()
            if isinstance(exc, FDAbortScript) and abort is None:
                abort = exc
        if abort is not None:
            raise abort

        await self._drain_pending_inline(ctx)

    async def await_sync_tasks(self, ctx) -> None:
        return