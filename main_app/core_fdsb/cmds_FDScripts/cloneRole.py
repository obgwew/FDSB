# cmds_FDScripts/cloneRole.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, FDEnvironmentError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild = ctx.message.guild
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$cloneRole` — this command can only be used inside a server (not in DMs)."
        ))
        return

    if len(args) < 1:
        await _send_error(ch, FDLogicError(
            "`$cloneRole` requires at least 1 argument: `$cloneRole[role id or @mention; optional new name]`"
        ))
        return

    role_raw = ctx.resolve(args[0]).strip()
    role_id_str = re.sub(r'[<@&>]', '', role_raw)
    
    try:
        role_id = int(role_id_str)
    except ValueError:
        await _send_error(ch, FDLogicError(
            f"`$cloneRole` — Invalid Role ID or Mention '{role_raw}'."
        ))
        return

    role = guild.get_role(role_id)

    if role is None:
        await _send_error(ch, FDEnvironmentError(
            f"`$cloneRole` — Role with ID {role_id} not found in this server."
        ))
        return

    new_role_name = role.name
    if len(args) > 1 and args[1].strip():
        new_role_name = ctx.resolve(args[1]).strip()

    try:
        new_role = await guild.create_role(
            name=new_role_name,
            permissions=role.permissions,
            color=role.color,
            hoist=role.hoist,
            mentionable=role.mentionable,
            reason=f"Cloned from '{role.name}' via FDScript"
        )
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$cloneRole` — Cannot clone role. The bot lacks 'Manage Roles' permission."
        ))
        return
    except discord.HTTPException:
        await _send_error(ch, FDEnvironmentError(
            f"`$cloneRole` — Failed to clone role '{role.name}' due to a Discord API error."
        ))
        return

    ctx.stop_typing()
    ctx.log_event(f"cloneRole → Cloned role '{role.name}' to '{new_role.name}' ({new_role.id})")