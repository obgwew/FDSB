# cmds_FDScripts/year.py
from datetime import datetime

import discord
from FDScript import ExecutionContext, Command


def _now_value(ctx: ExecutionContext) -> str:
    value = datetime.now().strftime("%Y")
    ctx.log_event(f"year -> {value}")
    return value


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return _now_value(ctx)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    await ch.send(_now_value(ctx))