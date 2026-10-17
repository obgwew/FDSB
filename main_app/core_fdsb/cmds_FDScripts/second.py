# cmds_FDScripts/second.py
# $second -> current second (00-59)
from datetime import datetime

import discord
from FDScript import ExecutionContext, Command


def _now_value(ctx: ExecutionContext) -> str:
    tz = getattr(ctx, "timezone", None)
    now = datetime.now(tz) if tz else datetime.now()
    value = now.strftime("%S")
    ctx.log_event(f"second -> {value}")
    return value


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return _now_value(ctx)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    await ch.send(_now_value(ctx))