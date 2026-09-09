# cmds_FDScripts/changeUsername.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, FDEnvironmentError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild = ctx.message.guild
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$changeUsername` — this command can only be used inside a server (not in DMs)."
        ))
        return

    if len(args) < 2:
        await _send_error(ch, FDLogicError(
            "`$changeUsername` requires 2 arguments: `$changeUsername[user ID/mention; new name]`"
        ))
        return

    user_raw = ctx.resolve(args[0]).strip()
    new_name = ctx.resolve(args[1]).strip()

    user_id_str = re.sub(r'[<@!>]', '', user_raw)
    if not user_id_str.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$changeUsername` — Invalid user ID or mention '{user_raw}'."
        ))
        return

    user_id = int(user_id_str)
    member = guild.get_member(user_id)

    if member is None:
        await _send_error(ch, FDEnvironmentError(
            f"`$changeUsername` — Member with ID {user_id} not found in this server."
        ))
        return

    try:
        await member.edit(nick=new_name if new_name else None)
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            f"`$changeUsername` — Cannot change nickname for {member.name}. Role hierarchy or missing permissions."
        ))
        return
    except discord.HTTPException:
        await _send_error(ch, FDEnvironmentError(
            "`$changeUsername` — Failed to change nickname due to a Discord API error."
        ))
        return

    ctx.stop_typing()
    ctx.log_event(f"changeUsername → Changed nickname for {member.name} to '{new_name}'")