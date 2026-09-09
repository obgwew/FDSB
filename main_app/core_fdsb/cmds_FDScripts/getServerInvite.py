# cmds_FDScripts/getServerInvite.py
import discord
from FDScript import ExecutionContext, Command, FDEnvironmentError, FDLogicError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    guild = ctx.message.guild
    if guild and guild.vanity_url:
        return guild.vanity_url
    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild = ctx.message.guild 
    
    if args and args[0].strip():
        guild_id_raw = ctx.resolve(args[0]).strip() 
        try:
            guild_id = int(guild_id_raw)
            if hasattr(ctx, 'bot'):
                guild = ctx.bot.get_guild(guild_id)
            elif hasattr(ctx.message, '_state'):
                guild = ctx.message._state._get_guild(guild_id)
        except ValueError:
            await _send_error(ch, FDLogicError(
                f"`$getServerInvite` — Invalid Server ID '{guild_id_raw}'. It must be a valid number."
            ))
            return

    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$getServerInvite` — Could not find the server. The bot must be a member of it."
        ))
        return

    invite_url = ""

    if guild.vanity_url:
        invite_url = guild.vanity_url
    else:
        valid_channels = [
            c for c in guild.text_channels 
            if c.permissions_for(guild.me).create_instant_invite
        ]
        
        if not valid_channels:
            await _send_error(ch, FDEnvironmentError(
                f"`$getServerInvite` — The bot lacks 'Create Invite' permissions in {guild.name}."
            ))
            return
            
        target_channel = valid_channels[0]
        
        try:
            invite = await target_channel.create_invite(max_age=0, max_uses=0, reason="Generated via $getServerInvite")
            invite_url = invite.url
        except discord.HTTPException:
            await _send_error(ch, FDEnvironmentError(
                "`$getServerInvite` — Failed to create the invite due to a Discord API error."
            ))
            return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(invite_url)
    ctx.last_bot_message = sent
    ctx.log_event(f"getServerInvite → {invite_url} (Guild: {guild.name})")