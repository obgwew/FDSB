# cmds_FDScripts/getUserStatus.py
import discord
import re
from FDScript import ExecutionContext, Command, FDLogicError, FDEnvironmentError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    guild = ctx.message.guild
    if guild is None:
        return "offline"

    if args and args[0].strip():
        user_raw = ctx.resolve(args[0]).strip()
        user_id_str = re.sub(r'[<@!>]', '', user_raw)
        
        try:
            user_id = int(user_id_str)
        except ValueError:
            ctx._abort_with_error(FDLogicError(
                f"`$getUserStatus` — Invalid User ID or mention '{user_raw}'."
            ))
            return ""
    else:
        user_id = ctx.message.author.id

    member = guild.get_member(user_id)
    
    if member:
        return str(member.status)
    return "offline"


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild = ctx.message.guild
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$getUserStatus` — this command can only be used inside a server (not in DMs)."
        ))
        return

    if args and args[0].strip():
        user_raw = ctx.resolve(args[0]).strip()
        user_id_str = re.sub(r'[<@!>]', '', user_raw)
        
        try:
            user_id = int(user_id_str)
        except ValueError:
            await _send_error(ch, FDLogicError(
                f"`$getUserStatus` — Invalid User ID or mention '{user_raw}'."
            ))
            return
    else:
        user_id = ctx.message.author.id

    member = guild.get_member(user_id)
    status_str = str(member.status) if member else "offline"

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(status_str)
    ctx.last_bot_message = sent
    ctx.log_event(f"getUserStatus → {status_str} (User ID: {user_id})")