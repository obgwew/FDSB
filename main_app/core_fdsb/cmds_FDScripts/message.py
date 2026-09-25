# cmds_FDScripts/message.py
import discord
from FDScript import ExecutionContext, Command


def _to_raw(text: str) -> str:
    if not text:
        return ""
    return text.replace('$', '$\u200b')


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not getattr(ctx, 'message', None) or not ctx.message.content:
        return ""

    full = ctx.message.content.strip()

    if not args:
        if getattr(ctx, 'is_event', False):
            return _to_raw(full)
        parts = full.split(None, 1)
        raw_msg = parts[1] if len(parts) > 1 else ""
        return _to_raw(raw_msg)

    if getattr(ctx, 'is_event', False):
        parts = full.split()
    else:
        parts = full.split(None, 1)
        parts = parts[1].split() if len(parts) > 1 else []

    try:
        idx = int(ctx.resolve(args[0]).strip())
        if 1 <= idx <= len(parts):
            return _to_raw(parts[idx - 1])
    except ValueError:
        pass

    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    res = resolve_inline(cmd.args, ctx)

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(res) if res else await dest.send("*(no arguments)*")
    ctx.last_bot_message = sent
    ctx.log_event(f"message → {res!r}")