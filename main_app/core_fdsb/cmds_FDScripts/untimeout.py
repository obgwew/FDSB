# cmds_FDScripts/untimeout.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError, _send_error
)

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$untimeout` requires a user mention or ID — example: `$untimeout[@user]`"
        ))
        return

    user_str = "".join(ctx.resolve(arg) for arg in args).strip()

    match_user = re.search(r"(\d+)", user_str)
    if not match_user:
        await _send_error(ch, FDLogicError(
            f"`$untimeout` — could not parse user from: `{user_str}`. Please provide a valid mention or User ID."
        ))
        return
    
    user_id = int(match_user.group(1))

    guild = ctx.message.guild
    if not guild:
        await _send_error(ch, FDEnvironmentError(
            "`$untimeout` can only be used within a server (guild)."
        ))
        return

    member = guild.get_member(user_id)
    if not member:
        try:
            member = await guild.fetch_member(user_id)
        except discord.NotFound:
            await _send_error(ch, FDLogicError(
                f"`$untimeout` — user with ID `{user_id}` was not found in this server."
            ))
            return
        except discord.HTTPException as ex:
            ctx.log_event(f"warning: failed to fetch member `{user_id}`: {ex}")
            return

    try:
        await member.timeout(None, reason=f"FDScript untimeout invoked by {ctx.message.author}")
        
        ctx.log_event(f"untimeout → successfully removed timeout from {member.name} ({user_id})")
        
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            f"`$untimeout` — bot lacks permission to remove timeout from `{member.name}`. "
            "Ensure the bot has 'Moderate Members' permission and its highest role is above the target user."
        ))
    except discord.HTTPException as ex:
        ctx.log_event(f"warning: unexpected HTTP error during $untimeout: {ex}")