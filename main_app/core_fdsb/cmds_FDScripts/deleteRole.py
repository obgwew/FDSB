# cmds_FDScripts/deleteRole.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, FDEnvironmentError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild = ctx.message.guild
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$deleteRole` — this command can only be used inside a server (not in DMs)."
        ))
        return

    if len(args) < 1:
        await _send_error(ch, FDLogicError(
            "`$deleteRole` requires 1 argument: `$deleteRole[role id or @mention]`"
        ))
        return

    role_raw = ctx.resolve(args[0]).strip()
    role_id_str = re.sub(r'[<@&>]', '', role_raw)
    
    try:
        role_id = int(role_id_str)
    except ValueError:
        await _send_error(ch, FDLogicError(
            f"`$deleteRole` — Invalid Role ID or Mention '{role_raw}'."
        ))
        return

    role = guild.get_role(role_id)

    if role is None:
        await _send_error(ch, FDEnvironmentError(
            f"`$deleteRole` — Role with ID {role_id} not found in this server."
        ))
        return

    try:
        await role.delete()
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            f"`$deleteRole` — Cannot delete role '{role.name}'. The bot lacks permissions or the role is higher than the bot's top role."
        ))
        return
    except discord.HTTPException:
        await _send_error(ch, FDEnvironmentError(
            f"`$deleteRole` — Failed to delete role '{role.name}' due to a Discord API error."
        ))
        return

    ctx.stop_typing()
    ctx.log_event(f"deleteRole → Deleted role: {role.name} ({role_id})")