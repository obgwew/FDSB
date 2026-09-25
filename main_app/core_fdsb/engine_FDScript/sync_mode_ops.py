# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/sync_mode_ops.py

import asyncio


class SyncModeMixin:
    """
    $syncMode — everything BELOW it (until the end of the current block) is
    executed as ONE synchronized batch:

      • every step below is started at the same moment (asyncio tasks);
      • the batch is awaited as a single unit, and the script only moves on
        (or finishes) when ALL steps are done;
      • if any step aborts (FDAbortScript), the remaining steps are cancelled
        and the whole script aborts — they succeed or fail together;
      • guards ($onlyAdmin / $onlyIf) run first, before the batch starts;
      • $if/$while/$for/$call/$useChannel/$suppressErrors are barriers: the
        batch before them is finished first, then they run, then a new batch
        begins.

    A "step" is a command, a bare-text line, or a send command together with
    the $addButton/$wait lines that belong to it (kept together so buttons
    stay attached to the right message).
    """

    _SYNC_CLOSERS  = ("endif", "elif", "else", "endwhile", "endfor", "break")
    _SYNC_GUARDS   = ("onlyAdmin", "onlyIf")
    _SYNC_BARRIERS = ("useChannel", "suppressErrors", "syncMode")

    # ── $syncMode as a plain command (only reached outside _execute) ──
    async def _exec_sync_mode(self, cmd, ctx) -> None:
        ctx.log_event("syncMode → (no commands below it in this block)")

    # ── Called from Interpreter._execute when it meets $syncMode ──────
    # `start` = index of the first token AFTER $syncMode.
    # Returns the index where the block stopped (a closer token or end).
    async def _exec_sync_block(self, tokens: list, start: int, ctx) -> int:
        from FDCore import Command

        ctx.log_event("syncMode → commands below run together as one batch")

        steps: list[tuple[int, int]] = []   # (head_index, end_index_exclusive)

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
                # Guards run first (before any step starts) so a failed
                # $onlyAdmin stops the script before anything is sent.
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

    # ── Where does the step that starts at `i` end? ────────────────────
    # Mirrors the look-ahead in _exec_command_with_lookahead / _collect_trailing_buttons
    def _sync_step_end(self, tokens: list, i: int) -> int:
        from FDCore import Command

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

    # ── Run a single step (uses the normal, order-preserving code path) ──
    async def _sync_run_step(self, tokens: list, head: int, end: int, ctx, serialize_view: bool = False) -> None:
        tok = tokens[head]
        # ctx.view is shared state. When this batch builds buttons, every step
        # that can send/attach a message takes the same lock, so a button-less
        # message can never grab a half-built view.
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
        from FDCore import FDAbortScript
        try:
            await self._sync_run_step(tokens, head, end, ctx, serialize_view)
        except (FDAbortScript, asyncio.CancelledError):
            raise
        except Exception as e:
            ctx.log_event(f"warning: syncMode step failed: {e}")

    # ── Start every step together and wait for the whole group ──────────
    async def _sync_run_batch(self, tokens: list, steps: list, ctx) -> None:
        from FDCore import FDAbortScript

        if not steps:
            return

        ctx.log_event(f"syncMode → launching {len(steps)} step(s) together")
        from FDCore import Command
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

    # ── Kept for compatibility with Interpreter.run() ───────────────────
    async def await_sync_tasks(self, ctx) -> None:
        return