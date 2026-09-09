# cmds_FDScripts/timeout.py
import datetime
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError, _send_error
)

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved_args = [ctx.resolve(arg) for arg in args]

    if len(resolved_args) < 2:
        await _send_error(ch, FDLogicError(
            "`$timeout` requires a time and a user separated by a semicolon `;` — "
            "example: `$timeout[1h; @user]`"
        ))
        return

    time_str = resolved_args[0].strip()
    user_str = resolved_args[1].strip()

    match_time = re.match(r"^(\d+)([smhd])$", time_str.lower())
    if not match_time:
        await _send_error(ch, FDLogicError(
            f"`$timeout` — invalid time format: `{time_str}`. "
            "Use numbers followed by s (seconds), m (minutes), h (hours), or d (days)."
        ))
        return

    amount = int(match_time.group(1))
    unit = match_time.group(2)

    multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    seconds = amount * multipliers[unit]

    if seconds > 2419200:
        await _send_error(ch, FDLogicError(
            "`$timeout` — duration cannot exceed 28 days."
        ))
        return

    match_user = re.search(r"(\d+)", user_str)
    if not match_user:
        await _send_error(ch, FDLogicError(
            f"`$timeout` — could not parse user from: `{user_str}`. Please provide a valid mention or User ID."
        ))
        return

    user_id = int(match_user.group(1))

    guild = ctx.message.guild
    if not guild:
        await _send_error(ch, FDEnvironmentError(
            "`$timeout` can only be used within a server (guild)."
        ))
        return

    member = guild.get_member(user_id)
    if not member:
        try:
            member = await guild.fetch_member(user_id)
        except discord.NotFound:
            await _send_error(ch, FDLogicError(
                f"`$timeout` — user with ID `{user_id}` was not found in this server."
            ))
            return
        except discord.HTTPException as ex:
            ctx.log_event(f"warning: failed to fetch member `{user_id}`: {ex}")
            return

    try:
        duration = datetime.timedelta(seconds=seconds)
        await member.timeout(duration, reason=f"FDScript timeout invoked by {ctx.message.author}")
        ctx.log_event(f"timeout → successfully timed out {member.name} ({user_id}) for {time_str}")

    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            f"`$timeout` — bot lacks permission to timeout `{member.name}`. "
            "Ensure the bot has 'Moderate Members' permission and its highest role is above the target user."
        ))
    except discord.HTTPException as ex:
        ctx.log_event(f"warning: unexpected HTTP error during $timeout: {ex}")