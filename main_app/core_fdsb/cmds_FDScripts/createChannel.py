import discord
import re
from FDScript import ExecutionContext, Command, _send_error, FDLogicError, FDRuntimeError, FDEnvironmentError

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:

    if len(args) < 2:
        await _send_error(ch, FDLogicError("`$createChannel` requires at least 2 arguments: `$createChannel[name; type; (category ID)]`"))
        return
        
    name = args[0].strip()
    c_type = args[1].strip().lower()
    cat_id_str = args[2].strip() if len(args) > 2 else None
    
    guild = ctx.message.guild if getattr(ctx, "message", None) else None
    if not guild:
        await _send_error(ch, FDEnvironmentError("`$createChannel` can only be used inside a server."))
        return
        
    if ctx.bot.user:
        bot_member = guild.get_member(ctx.bot.user.id)
        if bot_member and not bot_member.guild_permissions.manage_channels:
            await _send_error(ch, FDRuntimeError("Bot lacks `Manage Channels` permission to create a channel."))
            return
            
    category = None
    if cat_id_str:
        match = re.match(r'^<#(\d+)>$', cat_id_str)
        parsed_id = int(match.group(1)) if match else (int(cat_id_str) if cat_id_str.isdigit() else None)
        
        if parsed_id:
            category = guild.get_channel(parsed_id)
            if category and not isinstance(category, discord.CategoryChannel):
                await _send_error(ch, FDLogicError(f"`$createChannel` — Provided ID `{cat_id_str}` is not a category."))
                return
    
    try:
        if c_type == "text":
            new_channel = await guild.create_text_channel(name=name, category=category)
        elif c_type == "voice":
            new_channel = await guild.create_voice_channel(name=name, category=category)
        elif c_type == "category":
            new_channel = await guild.create_category(name=name)
        elif c_type == "forum":
            new_channel = await guild.create_forum(name=name, category=category)
        elif c_type == "stage":
            new_channel = await guild.create_stage_channel(name=name, category=category)
        else:
            await _send_error(ch, FDLogicError(f"`$createChannel` — Unsupported channel type: `{c_type}`. Valid types: text, voice, category, forum, stage."))
            return
            
        ctx.log_event(f"createChannel → created '{name}' ({c_type}) [ID: {new_channel.id}]")
        
    except discord.Forbidden:
        await _send_error(ch, FDRuntimeError("Bot does not have permission to create the channel."))
    except discord.HTTPException as e:
        await _send_error(ch, FDRuntimeError(f"Failed to create channel: {e.text}"))