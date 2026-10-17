# cmds_FDScripts/time.py
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo, available_timezones

import discord

from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError,
    _send_error,
)


@lru_cache(maxsize=1)
def _tz_lookup() -> dict[str, str]:
    return {name.lower(): name for name in available_timezones()}


def _find_tz(tz_raw: str) -> ZoneInfo | None:
    name = _tz_lookup().get(tz_raw.strip().lower().replace(" ", "_"))
    return ZoneInfo(name) if name else None


def get_now(ctx: ExecutionContext) -> datetime:
    tz = getattr(ctx, "timezone", None)
    return datetime.now(tz) if tz else datetime.now().astimezone()


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args or not args[0].strip():
        ctx._abort_with_error(FDSyntaxError("`$time` — requires a timezone, e.g. `$time[Asia/Amman]`"))
    tz_raw = ctx.resolve(args[0]).strip()
    tz = _find_tz(tz_raw)
    if tz is None:
        ctx._abort_with_error(FDLogicError(
            f"`$time` — unknown timezone `{tz_raw}`. Use a TZ database name like `Asia/Amman`."
        ))
    ctx.timezone = tz
    ctx.log_event(f"time → timezone set to {tz.key}")
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args or not args[0].strip():
        await _send_error(ch, FDSyntaxError("`$time` — requires a timezone, e.g. `$time[Asia/Amman]`"))
        return

    tz_raw = ctx.resolve(args[0]).strip()
    tz = _find_tz(tz_raw)
    if tz is None:
        await _send_error(ch, FDLogicError(
            f"`$time` — unknown timezone `{tz_raw}`. Use a TZ database name like `Asia/Amman`."
        ))
        return

    ctx.timezone = tz
    ctx.log_event(f"time → timezone set to {tz.key}")