# cmds_FDScripts/deleteIn.py
import asyncio
import re
import discord

from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError, FDRuntimeError, FDAbortScript,
    _send_error,
)
from main_app.core_fdsb.engine_FDScript.channel_wrappers import NormalChannelWrapper

_UNITS = {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
_PART_RE = re.compile(r"(\d+(?:\.\d+)?)(ms|s|m|h|d|w)")
_MAX_SECONDS = 14 * 86400


def _parse_duration(text: str) -> float | None:
    text = text.strip().lower().replace(" ", "")
    if not text:
        return None
    pos = 0
    total = 0.0
    for m in _PART_RE.finditer(text):
        if m.start() != pos:
            return None
        total += float(m.group(1)) * _UNITS[m.group(2)]
        pos = m.end()
    if pos != len(text):
        return None
    return total

def _schedule_delete(ctx: ExecutionContext, msg: discord.Message, seconds: float):
    key = getattr(msg, 'id', None)
    if key is None:
        return

    scheduled = getattr(ctx, '_delete_scheduled', None)
    if scheduled is None:
        scheduled = ctx._delete_scheduled = set()
    if key in scheduled:
        return
    scheduled.add(key)

    async def _run():
        chan = getattr(msg, 'channel', None)
        channel_id = getattr(chan, 'id', None) or getattr(msg, 'channel_id', None)
        err = None
        try:
            await asyncio.sleep(seconds)
            if getattr(ctx, 'ephemeral', False) and ctx.interaction is not None:
                await msg.delete()
            elif channel_id is not None and ctx.bot is not None:
                await ctx.bot.http.delete_message(channel_id, key)
            else:
                await msg.delete()
        except discord.NotFound:
            err = FDEnvironmentError(
                f"`$deleteIn` — cannot delete message `{key}`: it was already deleted"
            )
        except discord.Forbidden:
            err = FDEnvironmentError(
                f"`$deleteIn` — cannot delete message `{key}`: the bot has no permission to delete it"
            )
        except asyncio.CancelledError:
            raise
        except FDAbortScript:
            return
        except Exception as e:
            err = FDRuntimeError(f"`$deleteIn` — could not delete message `{key}`: {e}")
        if err is None:
            return

        try:
            if ctx.interaction is not None:
                dest = await ctx._real_dest()
            else:
                target = chan
                if target is None and channel_id is not None and ctx.bot is not None:
                    target = ctx.bot.get_channel(channel_id)
                dest = NormalChannelWrapper(target, ctx) if target is not None else None
            await _send_error(dest, err)
        except FDAbortScript:
            pass
        except Exception as e:
            print(f"[FDScript] $deleteIn: {err.msg} (could not report: {e})")

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        main_loop = getattr(ctx, '_main_loop', None)
        if main_loop is not None:
            asyncio.run_coroutine_threadsafe(_run(), main_loop)
        return

    tasks = getattr(ctx, '_delete_tasks', None)
    if tasks is None:
        tasks = ctx._delete_tasks = set()
    task = loop.create_task(_run())
    tasks.add(task)
    task.add_done_callback(tasks.discard)


def _set_delete_after(self: ExecutionContext, seconds: float):
    self.delete_after = seconds
    last_msg = getattr(self, '_last_bot_message', None)
    if last_msg is not None:
        _schedule_delete(self, last_msg, seconds)

def _inject_into_context():
    if getattr(ExecutionContext, '_delete_in_injected', False):
        return

    def _get_last_bot_message(self):
        return getattr(self, '_last_bot_message', None)

    def _set_last_bot_message(self, msg):
        self._last_bot_message = msg
        delete_after = getattr(self, 'delete_after', None)
        if msg is not None and delete_after is not None:
            _schedule_delete(self, msg, delete_after)

    ExecutionContext.last_bot_message = property(_get_last_bot_message, _set_last_bot_message)
    ExecutionContext.set_delete_after = _set_delete_after
    ExecutionContext._delete_in_injected = True

_inject_into_context()

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args or not args[0].strip():
        await _send_error(ch, FDSyntaxError("`$deleteIn` — requires a duration, e.g. `$deleteIn[3s]`"))
        return
    if len(args) > 1:
        await _send_error(ch, FDSyntaxError("`$deleteIn` — takes exactly one argument: `$deleteIn[Duration]`"))
        return

    raw = ctx.resolve(args[0]).strip()
    seconds = _parse_duration(raw)
    if seconds is None:
        await _send_error(ch, FDLogicError(
            f"`$deleteIn` — invalid duration `{raw}`. Use a number with a unit, "
            f"e.g. `3s`, `30s`, `1m`, `2h`, `1d`, `1h30m`."
        ))
        return
    if seconds <= 0:
        await _send_error(ch, FDLogicError("`$deleteIn` — duration must be greater than zero"))
        return
    if seconds > _MAX_SECONDS:
        await _send_error(ch, FDLogicError(
            f"`$deleteIn` — duration `{raw}` is too long; the maximum is 14 days (`14d`)"
        ))
        return

    ctx.set_delete_after(seconds)
    ctx.log_event(f"deleteIn → bot response will be deleted after {raw} ({seconds:g}s)")