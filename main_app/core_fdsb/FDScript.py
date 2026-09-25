# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/FDScript.py 
# FDScript.py — Interpreter & Public API
# ─────────────────────────────────────────────────────────────

import asyncio
import importlib
import inspect
import re
import io
import sys
import discord

from . import FDCore as _FDCore_module

sys.modules.setdefault('FDScript', sys.modules[__name__])
sys.modules.setdefault('FDCore', _FDCore_module)

try:
    from . import engine_FDScript as _engine_FDScript_module
    sys.modules.setdefault('engine_FDScript', _engine_FDScript_module)
except ImportError as e:
    print(f"[FDScript] warning: could not register 'engine_FDScript' package ({e}); "
          f"HTTP commands ($httpGet/$httpPost/...) and other engine-level "
          f"helpers may fail to load.")

from .FDCore import (
    set_vars_dir,
    set_bot_start_time,
    get_reserved_names,
    ExecutionContext,
    Command,
    TextToken,
    tokenise_line,
    _split_args,
    _send_error,
    _truncate,
    _parse_separator,
    _resolve_dm_target,
    _resolve_permission,
    _CHANNEL_TYPES,
    _PERMISSION_NAMES,
    _REACTIONS_MAX,
    _extract_all_emojis,
    _LOG_CHAR_LIMIT,
    _LOG_FILE_LIMIT,
    _parse_color,
    _NAMED_COLORS,
    _CLEAR_DEFAULT,
    _CLEAR_MAX,
    _load_data,
    _save_data,
    _scan_suppress_errors,
    _BOT_START_TIME,
    _format_uptime,
    _build_timestamp,
    _cooldowns,
    FDSyntaxError,
    FDLogicError,
    FDRuntimeError,
    FDEnvironmentError,
    FDAbortScript,
    register_inline_resolver,
    register_command_loader,
)

from .engine_FDScript.control_flow import ControlFlowMixin
from .engine_FDScript.functions_ops import FunctionsMixin
from .engine_FDScript.sync_mode_ops import SyncModeMixin

# ─────────────────────────────────────────────
# Command Registry
# ─────────────────────────────────────────────

def _load_cmd(name: str):
    package_name = __package__ or ''
    try:
        if package_name:
            return importlib.import_module(f".cmds_FDScripts.{name}", package=package_name)
        return importlib.import_module(f"cmds_FDScripts.{name}")
    except ModuleNotFoundError:
        return None

def _resolve_inline_cmd(cmd_name: str, args: list, ctx) -> 'str | None':
    module = _load_cmd(cmd_name)
    if module and hasattr(module, 'resolve_inline'):
        fn = module.resolve_inline
        if inspect.iscoroutinefunction(fn):
            raise RuntimeError(
                f"Plugin '{cmd_name}' has an async resolve_inline() but inline "
                f"resolution is synchronous. Make it a plain (non-async) function, "
                f"or remove '{cmd_name}' from _INLINE_WITH_ARGS so it only runs "
                f"as a standalone statement via execute()."
            )
        return fn(args, ctx)
    return None

register_inline_resolver(_resolve_inline_cmd)
register_command_loader(_load_cmd)

# ─────────────────────────────────────────────
# Condition Evaluator 
# ─────────────────────────────────────────────

_OPS = ("==", "!=", "=!", ">=", "<=", "=>", "=<", ">", "<")

def _find_comparison_operator(expr: str) -> tuple[str, str, str] | None:
    depth = 0
    in_quote = None
    i = 0
    n = len(expr)

    while i < n:
        ch = expr[i]

        if ch in ('"', "'"):
            if in_quote == ch:
                in_quote = None
            elif in_quote is None:
                in_quote = ch
            i += 1
            continue

        if in_quote is None:
            if ch == '[':
                depth += 1
                i += 1
                continue
            elif ch == ']':
                depth = max(0, depth - 1)
                i += 1
                continue

            if depth == 0:
                for op in _OPS:
                    if expr.startswith(op, i):
                        left = expr[:i].strip()
                        right = expr[i + len(op):].strip()
                        return left, op, right
        i += 1
    return None

def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        return s[1:-1]
    return s

def evaluate_condition(expr: str, ctx: ExecutionContext) -> bool:
    expr = expr.strip()
    if not expr:
        return False

    comp = _find_comparison_operator(expr)
    if comp is not None:
        left_raw, op, right_raw = comp

        left_val = _strip_quotes(ctx.resolve(left_raw).strip())
        right_val = _strip_quotes(ctx.resolve(right_raw).strip())

        try:
            l_num, r_num = float(left_val), float(right_val)
            if op == "==": return l_num == r_num
            if op in ("!=", "=!"): return l_num != r_num
            if op in (">=", "=>"): return l_num >= r_num
            if op in ("<=", "=<"): return l_num <= r_num
            if op == ">":  return l_num >  r_num
            if op == "<":  return l_num <  r_num
        except ValueError:
            if op == "==": return left_val == right_val
            if op in ("!=", "=!"): return left_val != right_val
            if op in (">=", "=>"): return left_val >= right_val
            if op in ("<=", "=<"): return left_val <= right_val
            if op == ">":  return left_val >  right_val
            if op == "<":  return left_val <  right_val
        return False

    val = _strip_quotes(ctx.resolve(expr).strip())
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    return bool(val)

# ─────────────────────────────────────────────
# Position-Independent Directives
# ─────────────────────────────────────────────
class _PreScanDirectives:

    @staticmethod
    async def apply(interpreter: 'Interpreter', ctx: ExecutionContext) -> None:
        _PreScanDirectives._suppress_errors(interpreter, ctx)

    @staticmethod
    def _suppress_errors(interpreter: 'Interpreter', ctx: ExecutionContext) -> None:
        ctx.suppress_errors, ctx.suppress_errors_message = _scan_suppress_errors(interpreter.script_text)

# ─────────────────────────────────────────────
# Interpreter
# ─────────────────────────────────────────────

class Interpreter(ControlFlowMixin, FunctionsMixin, SyncModeMixin):
    _MAX_CALL_DEPTH = 50

    def __init__(self, script: str):
        self.script_text = script
        self.source_lines = script.splitlines()
        self.functions: dict[str, tuple[int, int]] = {}
        self._active_tokens: list = []

    # ── Main entry point ──────────────────────────────────────
    async def run(self, ctx: ExecutionContext):
        await _PreScanDirectives.apply(self, ctx)

        tokens = self._tokenise_all()
        errors = self._validate(tokens)

        ctx.is_global_reply = False
        
        if not hasattr(ctx, 'text_buffer'):
            ctx.text_buffer = ""

        if errors:
            err = errors[0]
            ch = getattr(ctx.message, 'channel', None)

            if ctx.suppress_errors:
                ctx.log_event(f"[suppressed] {err._category}: {err.msg}")
                if ctx.suppress_errors_message and ch is not None:
                    try:
                        await ch.send(ctx.suppress_errors_message)
                    except Exception as e:
                        print(f"[FDScript] Failed to send suppressed-error message: {e}")
                return

            msg = f"{err._icon} **{err._category}** — {err.msg}"
            if ch is not None:
                await ch.send(msg)
            else:
                print(f"[Error] {err._category}: {err.msg}")
            return

        self.functions = self._collect_functions(tokens)
        self._active_tokens = tokens

        try:
            await self._execute(tokens, ctx)

            if hasattr(self, 'await_sync_tasks'):
                await self.await_sync_tasks(ctx)

            await self._drain_pending_inline(ctx)

            await self._flush_message(ctx)
            
        except FDAbortScript:
            ctx.log_event("script execution aborted due to error.")
            
        except Exception as e:
            ctx.log_event(f"Unhandled crash: {e}")
            print(f"[FDScript] Unhandled exception: {e}")

        await self._flush_logs(ctx)

    # ── Flush final message (Text + Embed(s) + Buttons) ────────
    async def _flush_message(self, ctx: ExecutionContext):
        text_content = getattr(ctx, 'text_buffer', "").strip()
        embeds = [
            builder.build()
            for _, builder in sorted(ctx.embed_builders.items())
            if builder.is_set()
        ]
        has_embed = bool(embeds)
        has_view = bool(ctx.view and ctx.view.children)

        if not text_content and not has_embed and not has_view:
            return

        ctx.stop_typing()
        ch = await ctx.get_dest()

        kwargs = {}
        if text_content:
            kwargs['content'] = text_content
        if has_embed:
            kwargs['embeds'] = embeds
        if has_view:
            kwargs['view'] = ctx.view

        try:
            if getattr(ctx, "is_global_reply", False):
                sent = await ctx.message.reply(**kwargs)
            else:
                sent = await ch.send(**kwargs)
            ctx.last_bot_message = sent
            ctx.log_event("buffered message → sent")
        except discord.HTTPException as e:
            ctx.log_event(f"Failed to send buffered message: {e}")
            print(f"[FDScript] Buffered message send error: {e}")

    # ── Flush a standalone $addButton chain (no text/embed) ────
    async def _flush_view_only(self, ctx: ExecutionContext):
        if not (ctx.view and ctx.view.children):
            return

        ctx.stop_typing()
        ch = await ctx.get_dest()

        try:
            if getattr(ctx, "is_global_reply", False):
                sent = await ctx.message.reply(view=ctx.view)
            else:
                sent = await ch.send(view=ctx.view)
            ctx.last_bot_message = sent
            ctx.log_event("buttons-only message → sent")
        except discord.HTTPException as e:
            ctx.log_event(f"Failed to send buttons-only message: {e}")
            print(f"[FDScript] buttons-only send error: {e}")
        finally:
            ctx.view = None

    # ── Flush pending log snapshots ───────────────────────────
    async def _flush_logs(self, ctx: ExecutionContext):
        ch = ctx.message.channel if getattr(ctx, 'message', None) else None

        for pending in ctx._pending_logs:
            try:
                target_ch = ctx.bot.get_channel(pending.channel_id)
                if not target_ch:
                    if ch:
                        try:
                            await ch.send(
                                f"🔵 **Environment Error** — "
                                f"`$log` — channel `{pending.channel_id}` not found or bot has no access"
                            )
                        except Exception:
                            pass
                    continue

                label     = f"[FDScript Log{f' — {pending.name_code}' if pending.name_code else ''}]"
                body      = "\n".join(pending.entries) if pending.entries else "(no events in this range)"
                full_text = f"{label}\n{body}"
                block     = f"```\n{full_text}\n```"

                if len(block) <= _LOG_CHAR_LIMIT:
                    await target_ch.send(block)
                else:
                    raw_bytes = full_text.encode("utf-8")
                    if len(raw_bytes) > _LOG_FILE_LIMIT:
                        if ch:
                            await ch.send("🟡 **Runtime Error** — `$log` — log snapshot exceeds the 10 MB file limit")
                        continue
                    safe_name = ''.join(
                        c if c.isalnum() or c in ('-', '_') else '_'
                        for c in pending.name_code
                    ).strip('_') or "fdscript_log"
                    await target_ch.send(
                        "📄 Log snapshot too large for a code block — sent as file:",
                        file=discord.File(fp=io.BytesIO(raw_bytes), filename=f"{safe_name}.txt")
                    )

            except Exception as e:
                print(f"[FDScript] _flush_logs failed for '{pending.name_code}': {e}")
            
    # ── Join multi-line commands before tokenising ────────────
    def _join_multiline(self) -> list[tuple[int, str]]:
        joined: list[tuple[int, str]] = []
        buffer: list[str] = []
        depth = 0
        start_line = 1

        for line_no, line in enumerate(self.source_lines, start=1):
            if not buffer:
                start_line = line_no

            for ch in line:
                if ch == '[': depth += 1
                elif ch == ']': depth -= 1
                elif ch == '#' and depth == 0: break

            buffer.append(line)

            if depth <= 0:
                joined.append((start_line, '\n'.join(buffer)))
                buffer = []
                depth = 0

        if buffer:
            joined.append((start_line, '\n'.join(buffer)))
        return joined

    # ── Tokenise all lines upfront ────────────────────────────
    def _tokenise_all(self) -> list:
        result = []
        for line_no, block in self._join_multiline():
            try:
                toks = tokenise_line(block, line_no)
                result.extend(toks)
            except SyntaxError as e:
                result.append(Command("__syntax_error__", [str(e)], block, line_no))
        return result

    # ── Validate ──────────────────────────────────────────────
    def _validate(self, tokens: list) -> list:
        stack = []
        OPENERS = {"if": "endif", "while": "endwhile", "for": "endfor", "func": "endfunc"}
        CLOSERS = {"endif": "if", "endwhile": "while", "endfor": "for", "endfunc": "func"}

        func_names = {
            tok.args[0].strip()
            for tok in tokens
            if isinstance(tok, Command) and tok.name == "func" and tok.args and tok.args[0].strip()
        }
        seen_func_names = set()

        for tok in tokens:
            if isinstance(tok, Command) and tok.name == "__syntax_error__":
                line_num = tok.line_no if tok.line_no is not None else '?'
                return [FDSyntaxError(f"Line {line_num}: {tok.args[0]}")]

            if isinstance(tok, Command) and tok.name == "__unknown__":
                line_num = tok.line_no if tok.line_no is not None else '?'
                return [FDSyntaxError(f"Line {line_num}: Unknown command `{tok.args[0]}`")]

            if isinstance(tok, str):
                continue

            line_num = tok.line_no if tok.line_no is not None else '?'

            if tok.name in OPENERS:
                stack.append((tok.name, line_num))
                if tok.name == "func":
                    name = tok.args[0].strip() if tok.args else ""
                    if not name:
                        return [FDLogicError(
                            f"Line {line_num}: `$func[]` — function name cannot be empty"
                        )]
                    if name in seen_func_names:
                        return [FDLogicError(
                            f"Line {line_num}: duplicate function `{name}` — "
                            f"already defined with `$func` elsewhere"
                        )]
                    seen_func_names.add(name)
                continue

            if tok.name in CLOSERS:
                expected = CLOSERS[tok.name]
                if not stack:
                    return [FDSyntaxError(f"Line {line_num}: `${tok.name}` without `${expected}`")]
                if stack[-1][0] != expected:
                    return [FDLogicError(f"Line {line_num}: `${tok.name}` does not match `${stack[-1][0]}`")]
                stack.pop()
                continue

            if tok.name == "break":
                if not any(t[0] in ("while", "for") for t in stack):
                    return [FDLogicError(f"Line {line_num}: `$break` outside loops")]
                continue

            if tok.name == "call":
                if not tok.args or not tok.args[0].strip():
                    return [FDLogicError(f"Line {line_num}: `$call[]` — function name cannot be empty")]
                raw = tok.args[0].strip()
                if '$' not in raw and raw not in func_names:
                    return [FDLogicError(
                        f"Line {line_num}: `$call[{raw}]` — no function named `{raw}` is defined "
                        f"(define it with `$func[{raw}] ... $endfunc`)"
                    )]
                continue

            if tok.name == "log" and (not tok.args or not tok.args[0].strip()):
                return [FDLogicError(f"Line {line_num}: `$log` requires at least a channel ID")]

            if tok.name == "dm" and tok.args and not any(a.strip() for a in tok.args):
                return [FDLogicError(f"Line {line_num}: `$dm[]` — target cannot be empty.")]

        if stack:
            opener, line_num = stack[0]
            return [FDSyntaxError(f"Line {line_num}: `${opener}` not closed with `${OPENERS[opener]}`")]

        return []

    # ── Append resolved text ──────────────────────────────────
    async def _append_text(self, ctx: ExecutionContext, tok) -> None:
        line_no = getattr(tok, 'line_no', None)
        ctx.set_line(line_no)
        resolved_text = ctx.resolve(tok)
        await self._drain_pending_inline(ctx)
        if not resolved_text.strip():
            return

        if ctx.text_buffer and not ctx.text_buffer.endswith("\n"):
            same_line = line_no is not None and getattr(ctx, '_last_text_line', None) == line_no
            if same_line:
                if not ctx.text_buffer.endswith((' ', '\t')):
                    ctx.text_buffer += ' '
            else:
                ctx.text_buffer += '\n'

        ctx.text_buffer += resolved_text
        ctx._last_text_line = line_no

    # ── Run coroutines queued by inline commands ───────────────────
    async def _drain_pending_inline(self, ctx: ExecutionContext) -> None:
        pending = ctx._pending_inline_actions
        if not pending:
            return
        ctx._pending_inline_actions = []
        for coro in pending:
            try:
                await coro
            except Exception as e:
                ctx.log_event(f"warning: inline action failed: {e}")

    async def _collect_trailing_buttons(self, tokens: list, next_idx: int, ctx: ExecutionContext):
        wait_cmd = None
        while next_idx < len(tokens):
            next_tok = tokens[next_idx]

            if isinstance(next_tok, str):
                if not next_tok.strip():
                    next_idx += 1
                    continue
                else:
                    break
            elif isinstance(next_tok, Command):
                    if next_tok.name == "addButton":
                        await self._exec_command(next_tok, ctx, tokens)
                        next_idx += 1
                        continue
                    elif next_tok.name == "wait" and wait_cmd is None:
                        wait_cmd = next_tok
                        next_idx += 1
                        break
                    else:
                        break
            else:
                break

        return next_idx, wait_cmd

    # ── Send a bare-text token now, same shape as $sendMessage ─────────
    async def _send_text_now(self, ctx: ExecutionContext, resolved_text: str) -> None:
        ctx.stop_typing()
        ch = await ctx.get_dest()
        view = ctx.view if ctx.view is not None else discord.utils.MISSING

        try:
            if getattr(ctx, "is_global_reply", False):
                sent = await ctx.message.reply(content=resolved_text, view=view)
            else:
                sent = await ch.send(resolved_text, view=view)
            ctx.last_bot_message = sent
            ctx.log_event(f"text → sent as message: {_truncate(resolved_text)!r}")
        except discord.HTTPException as e:
            ctx.log_event(f"Failed to send text message: {e}")
        finally:
            ctx.view = None

    async def _process_text_token(self, tokens: list, tok, next_idx: int, ctx: ExecutionContext) -> int:
        line_no = getattr(tok, 'line_no', None)
        ctx.set_line(line_no)

        capture = getattr(ctx, '_capture_out', None)
        if capture is not None:
            resolved_text = ctx.resolve(tok)
            await self._drain_pending_inline(ctx)
            if resolved_text.strip():
                capture.append(resolved_text.strip('\n'))
            return next_idx

        resolved_text = ctx.resolve(tok)
        await self._drain_pending_inline(ctx)

        if not resolved_text.strip():
            return next_idx

        next_idx, wait_cmd = await self._collect_trailing_buttons(tokens, next_idx, ctx)
        await self._send_text_now(ctx, resolved_text)

        if wait_cmd is not None:
            await self._exec_command(wait_cmd, ctx, tokens)

        return next_idx

    # ── Execute ───────────────────────────────────────────────
    async def _execute(self, tokens: list, ctx: ExecutionContext, start: int = 0) -> int:
        i = start
        while i < len(tokens):
            tok = tokens[i]
            i += 1

            if isinstance(tok, str):
                i = await self._process_text_token(tokens, tok, i, ctx)
                continue
                
            if tok.name == "if":
                i = await self._exec_if(tokens, i - 1, ctx)
                continue
            if tok.name == "while":
                i = await self._exec_while(tokens, i - 1, ctx)
                continue
            if tok.name == "for":
                i = await self._exec_for(tokens, i - 1, ctx)
                continue
            if tok.name == "func":
                i = self._find_closer(tokens, i, "func", "endfunc") + 1
                continue
            if tok.name == "syncMode":
                ctx.sync_mode = True
                ctx.log_event("syncMode enabled")
                continue
            if tok.name == "endfunc":
                continue
            if tok.name == "call":
                await self._exec_call(tok, tokens, ctx)
                continue
            if tok.name in ("endif", "endwhile", "endfor", "elif", "else"):
                return i - 1
            if tok.name == "break":
                return -1

            i = await self._exec_command_with_lookahead(tok, tokens, i, ctx)

        return i

    # ── $useChannel ──
    async def _exec_use_channel(self, cmd: Command, ctx: ExecutionContext) -> None:
        args = cmd.args
        if len(args) < 2:
            ctx.log_event("[useChannel] requires guildID and channelID")
            return

        guild_id_raw   = (ctx.resolve(args[0])).strip()
        channel_id_raw = (ctx.resolve(args[1])).strip()

        if not (guild_id_raw.isdigit() and channel_id_raw.isdigit()):
            ctx.log_event("[useChannel] guildID/channelID must be literal numeric IDs")
            return

        target_guild = ctx.bot.get_guild(int(guild_id_raw))
        if not target_guild:
            ctx.log_event(f"[useChannel] guild {guild_id_raw} not found (bot may not be a member)")
            return

        target_channel = target_guild.get_channel(int(channel_id_raw))
        if not target_channel:
            try:
                target_channel = await target_guild.fetch_channel(int(channel_id_raw))
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
                ctx.log_event(f"[useChannel] failed to fetch channel {channel_id_raw}: {e}")
                target_channel = None

        if not target_channel:
            ctx.log_event(f"[useChannel] channel {channel_id_raw} not found in guild {guild_id_raw}")
            return

        ctx._channel_override = target_channel
        ctx.log_event(
            f"useChannel → redirecting output (from this line onward) to channel "
            f"{channel_id_raw} (guild {guild_id_raw})"
        )

        if ctx.interaction and not ctx.interaction.response.is_done():
            try:
                await ctx.interaction.response.defer()
            except Exception as e:
                ctx.log_event(f"[useChannel] failed to defer interaction: {e}")
        ctx.interaction = None
        ctx.is_global_reply = False

    # ── command dispatch ──────────────────────────────────────
    async def _exec_command(self, cmd: Command, ctx: ExecutionContext, tokens: list | None = None) -> None:
        await self._expand_inline_calls(cmd.args, tokens, ctx)

        if cmd.name == "suppressErrors":
            return
        if cmd.name == "useChannel":
            await self._exec_use_channel(cmd, ctx)
            return
        if cmd.name == "syncMode":
            ctx.sync_mode = True
            ctx.log_event("syncMode enabled")
            return

        module = _load_cmd(cmd.name)
        ch = await ctx.get_dest()

        if module is None:
            await _send_error(ch, FDLogicError(f"Unknown command: `${cmd.name}`"))
            return

        if not hasattr(module, "execute"):
            await _send_error(ch, FDLogicError(
                f"`${cmd.name}` has no `execute()` — it may be an inline-only command "
                f"and can't be used as a standalone statement."
            ))
            return

        try:
            await module.execute(cmd, cmd.args, ctx, ch)
            await self._drain_pending_inline(ctx)
        except FDAbortScript:
            raise
        except Exception as e:
            await _send_error(ch, FDLogicError(f"`${cmd.name}` raised an error: `{e}`"))

    # ── command Lookahead Wrapper ────────────
    _SEND_COMMANDS = ("sendMessage", "sendEmbedMessage", "reply", "replyIn", "editMessage")

    async def _exec_command_with_lookahead(self, cmd: Command, tokens: list, next_idx: int, ctx: ExecutionContext) -> int:
        await self._expand_inline_calls(cmd.args, tokens, ctx)

        wait_cmd = None
        standalone_buttons = cmd.name == "addButton"
        is_edit_batch = cmd.name == "editButton"

        if standalone_buttons:
            await self._exec_command(cmd, ctx, tokens)

        if cmd.name in self._SEND_COMMANDS or standalone_buttons:
            while next_idx < len(tokens):
                next_tok = tokens[next_idx]
                
                if isinstance(next_tok, str):
                    if not next_tok.strip():
                        next_idx += 1
                        continue
                    else:
                        break 
                        
                elif isinstance(next_tok, Command):
                    if next_tok.name == "addButton":
                        await self._exec_command(next_tok, ctx)
                        next_idx += 1
                        continue
                    elif next_tok.name == "wait" and wait_cmd is None:
                        wait_cmd = next_tok
                        next_idx += 1
                        break
                    else:
                        break 
                else:
                    break

            if not standalone_buttons:
                await self._exec_command(cmd, ctx, tokens)
            elif wait_cmd is not None:
                await self._flush_view_only(ctx)

            if wait_cmd is not None:
                await self._exec_command(wait_cmd, ctx, tokens)

            return next_idx

        if is_edit_batch:
            edit_cmds = [cmd]
            while next_idx < len(tokens):
                next_tok = tokens[next_idx]

                if isinstance(next_tok, str):
                    if not next_tok.strip():
                        next_idx += 1
                        continue
                    else:
                        break

                elif isinstance(next_tok, Command):
                    if next_tok.name == "editButton":
                        edit_cmds.append(next_tok)
                        next_idx += 1
                        continue
                    elif next_tok.name == "wait" and wait_cmd is None:
                        wait_cmd = next_tok
                        next_idx += 1
                        break
                    else:
                        break
                else:
                    break

            for i, edit_cmd in enumerate(edit_cmds):
                is_last = (i == len(edit_cmds) - 1)
                module = _load_cmd("editButton")
                ch = await ctx.get_dest()
                if module and hasattr(module, "execute"):
                    await module.execute(edit_cmd, edit_cmd.args, ctx, ch, do_edit=is_last)
                await self._drain_pending_inline(ctx)

            if wait_cmd is not None:
                await self._exec_command(wait_cmd, ctx, tokens)

            return next_idx

        await self._exec_command(cmd, ctx)
        return next_idx

    # ── Condition evaluator ───────────────────────────────────
    def _evaluate(self, expr: str, ctx: ExecutionContext) -> bool:
        return evaluate_condition(expr, ctx)

# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

async def run_script(message: discord.Message, bot: discord.Client, script_text: str, is_event: bool = False, is_reply: bool = False, interaction: discord.Interaction = None):
    interpreter = Interpreter(script_text)
    ctx = ExecutionContext(message, bot, is_event=is_event, interaction=interaction)
    if is_reply:
        ctx.is_global_reply = True
    await interpreter.run(ctx)