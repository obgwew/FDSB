# cmds_FDScripts/serverOwnerID.py
import discord
from FDScript import ExecutionContext, Command, FDEnvironmentError, _send_error


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    guild = ctx.message.guild
    if guild is None:
        return ""
    
    return str(guild.owner_id)

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild = ctx.message.guild
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$serverOwnerID` — this command can only be used inside a server (not in DMs)."
        ))
        return

    result = str(guild.owner_id)

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"serverOwnerID → {result}")