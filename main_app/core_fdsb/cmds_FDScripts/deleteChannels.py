import discord
import re
from FDScript import ExecutionContext, Command, _send_error, FDLogicError, FDRuntimeError, FDEnvironmentError

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    
    if not args or not any(ctx.resolve(a).strip() for a in args):
        await _send_error(ch, FDLogicError("`$deleteChannels` requires at least one channel ID or mention."))
        return
        
    guild = ctx.message.guild if getattr(ctx, "message", None) else None
    if not guild:
        await _send_error(ch, FDEnvironmentError("`$deleteChannels` can only be used inside a server."))
        return

    deleted_count = 0
    
    for arg in args:
        target_str = ctx.resolve(arg).strip()
        if not target_str:
            continue
            
        match = re.match(r'^<#(\d+)>$', target_str)
        if match:
            channel_id = int(match.group(1))
        elif target_str.isdigit():
            channel_id = int(target_str)
        else:
            await _send_error(ch, FDLogicError(f"`$deleteChannels` — Invalid channel ID or mention: `{target_str}`"))
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            channel = ctx.bot.get_channel(channel_id)

        if channel:
            try:
                await channel.delete()
                deleted_count += 1
            except discord.Forbidden:
                await _send_error(ch, FDRuntimeError(f"Bot lacks permission to delete channel ID `{channel_id}`."))
                return
            except discord.HTTPException as e:
                await _send_error(ch, FDRuntimeError(f"Failed to delete channel `{channel_id}`: {e.text}"))
                return

    ctx.log_event(f"deleteChannels → deleted {deleted_count} channel(s)")