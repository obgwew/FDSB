import discord
import re
from FDScript import ExecutionContext, Command

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str | None:
    if not args or not args[0].strip():
        return "true"
        
    target_str = args[0].strip()
    match = re.match(r'^<#(\d+)>$', target_str)
    
    if match:
        channel_id = int(match.group(1))
    elif target_str.isdigit():
        channel_id = int(target_str)
    else:
        return "false"

    channel = ctx.bot.get_channel(channel_id)
    
    if not channel and getattr(ctx.message, "guild", None):
        channel = ctx.message.guild.get_channel(channel_id)

    return "true" if channel else "false"

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    value = resolve_inline(args, ctx) or "false"
    
    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(value)
    ctx.last_bot_message = sent
    
    arg_log = f"[{args[0]}]" if args and args[0].strip() else ""
    ctx.log_event(f"channelExists{arg_log} → {value!r}")