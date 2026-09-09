# cmds_FDScripts/roleAssign.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, FDEnvironmentError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild = ctx.message.guild
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$roleAssign` — this command can only be used inside a server."
        ))
        return

    if len(args) < 2:
        await _send_error(ch, FDLogicError(
            "`$roleAssign` requires at least 2 arguments: `$roleAssign[user; +role1; -role2; ...]`"
        ))
        return

    user_raw = ctx.resolve(args[0]).strip()
    user_id_str = re.sub(r'[<@!>]', '', user_raw)
    
    if not user_id_str.isdigit():
        await _send_error(ch, FDLogicError(f"`$roleAssign` — Invalid User ID/Mention: {user_raw}"))
        return

    member = guild.get_member(int(user_id_str))
    if member is None:
        await _send_error(ch, FDEnvironmentError(f"`$roleAssign` — Member {user_raw} not found."))
        return

    roles_to_add = []
    roles_to_remove = []

    for arg in args[1:]:
        raw_arg = ctx.resolve(arg).strip() 
        if not raw_arg:
            continue
            
        action = raw_arg[0] 
        role_part = raw_arg[1:] 
        
        role_id_str = re.sub(r'[<@&>]', '', role_part)
        
        if not role_id_str.isdigit():
            continue
            
        role = guild.get_role(int(role_id_str))
        if role:
            if action == '+':
                roles_to_add.append(role)
            elif action == '-':
                roles_to_remove.append(role)

    try:
        if roles_to_add:
            await member.add_roles(*roles_to_add)
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$roleAssign` — Missing permissions or role hierarchy issue."
        ))
        return
    except discord.HTTPException:
        await _send_error(ch, FDEnvironmentError(
            "`$roleAssign` — Failed to assign roles due to Discord API error."
        ))
        return

    ctx.stop_typing()
    ctx.log_event(f"roleAssign → Processed roles for {member.name}")