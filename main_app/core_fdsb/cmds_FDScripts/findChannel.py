import discord
import re
from FDScript import ExecutionContext, Command

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str | None:
    if not args or not args[0].strip():
        return ""

    target_str = args[0].strip()
    guild = ctx.message.guild if getattr(ctx, "message", None) else None
    
    if not guild:
        return ""

    match = re.match(r'^<#(\d+)>$', target_str)
    if match:
        channel_id = int(match.group(1))
        channel = guild.get_channel(channel_id)
        return str(channel.id) if channel else ""

    target_lower = target_str.lower()
    for channel in guild.channels:
        if channel.name.lower() == target_lower:
            return str(channel.id)

    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    value = resolve_inline(args, ctx) or ""
    
    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(value)
    ctx.last_bot_message = sent
    
    arg_log = f"[{args[0]}]" if args and args[0].strip() else ""
    ctx.log_event(f"findChannel{arg_log} → {value!r}")