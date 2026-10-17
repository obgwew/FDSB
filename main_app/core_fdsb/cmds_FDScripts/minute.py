# cmds_FDScripts/minute.py
# $minute -> current minute (00-59)
from datetime import datetime

import discord
from FDScript import ExecutionContext, Command


def _now_value(ctx: ExecutionContext) -> str:
    tz = getattr(ctx, "timezone", None)
    now = datetime.now(tz) if tz else datetime.now()
    value = now.strftime("%M")
    ctx.log_event(f"minute -> {value}")
    return value


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return _now_value(ctx)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    await ch.send(_now_value(ctx))