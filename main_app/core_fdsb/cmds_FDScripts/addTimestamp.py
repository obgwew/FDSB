# cmds_FDScripts/addTimestamp.py
import discord
from datetime import datetime, timezone
from FDScript import ExecutionContext, Command


def _resolve_index(args: list[str], ctx: ExecutionContext) -> int:
    if not args:
        return 1
    raw = (ctx.resolve(args[0])).strip()
    if not raw.isdigit():
        return 1
    return int(raw)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    index = _resolve_index(args, ctx)
    ctx.get_embed_builder(index).timestamp = datetime.now(timezone.utc)
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    index = _resolve_index(args, ctx)
    ctx.get_embed_builder(index).timestamp = datetime.now(timezone.utc)
    ctx.log_event(f"addTimestamp → set embed #{index} timestamp (renders next to footer)")