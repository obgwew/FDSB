# cmds_FDScripts/timeout.py
import datetime
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError, FDRuntimeError, _send_error,
)

_MAX_SECONDS = 28 * 86400
_UNITS       = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_DURATION_RE = re.compile(r"(?:\d+\s*[smhd]\s*)+")
_PART_RE     = re.compile(r"(\d+)\s*([smhd])")
_ID_RE       = re.compile(r"\d{15,25}")


def _parse_duration(text: str):
    t = text.strip().lower()
    if not _DURATION_RE.fullmatch(t):
        return None
    return sum(int(n) * _UNITS[u] for n, u in _PART_RE.findall(t))


def _guild_and_author(ctx: ExecutionContext):
    if ctx.interaction is not None:
        return ctx.interaction.guild, ctx.interaction.user
    msg = ctx.message
    return getattr(msg, "guild", None), getattr(msg, "author", None)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 2 or len(args) > 3:
        await _send_error(ch, FDSyntaxError(
            "`$timeout` requires a time and a user — `$timeout[time;user;(reason)]`, "
            "example: `$timeout[1h;@user]`"
        ))
        return

    first, second = ctx.resolve(args[0]).strip(), ctx.resolve(args[1]).strip()
    reason = ctx.resolve(args[2]).strip() if len(args) > 2 else ""

    seconds = _parse_duration(first)
    user_str = second
    if seconds is None:
        seconds = _parse_duration(second)
        user_str = first
    if seconds is None:
        await _send_error(ch, FDLogicError(
            f"`$timeout` — invalid time format: `{first}`. Use numbers followed by "
            "s (seconds), m (minutes), h (hours) or d (days), e.g. `30m` or `1h30m`."
        ))
        return
    if seconds <= 0:
        await _send_error(ch, FDLogicError("`$timeout` — duration must be greater than 0."))
        return
    if seconds > _MAX_SECONDS:
        await _send_error(ch, FDLogicError("`$timeout` — duration cannot exceed 28 days."))
        return

    m = _ID_RE.search(user_str)
    if not m:
        await _send_error(ch, FDLogicError(
            f"`$timeout` — could not parse user from: `{user_str}`. Please provide a valid mention or User ID."
        ))
        return
    user_id = int(m.group())

    guild, author = _guild_and_author(ctx)
    if guild is None:
        await _send_error(ch, FDEnvironmentError("`$timeout` can only be used within a server (guild)."))
        return

    if not guild.me.guild_permissions.moderate_members:
        await _send_error(ch, FDEnvironmentError("`$timeout` — bot lacks the `Moderate Members` permission."))
        return

    member = guild.get_member(user_id)
    if member is None:
        try:
            member = await guild.fetch_member(user_id)
        except discord.NotFound:
            await _send_error(ch, FDLogicError(
                f"`$timeout` — user with ID `{user_id}` was not found in this server."
            ))
            return
        except discord.HTTPException as ex:
            ctx.log_event(f"timeout → ✗ could not fetch member {user_id}: {ex}")
            await _send_error(ch, FDRuntimeError(f"`$timeout` — Discord API error: `{ex.text}`"))
            return

    if member.id == guild.owner_id or member.guild_permissions.administrator:
        await _send_error(ch, FDEnvironmentError(
            f"`$timeout` — `{member.name}` is the server owner or an Administrator; Discord does not allow timing them out."
        ))
        return
    if member.top_role >= guild.me.top_role:
        await _send_error(ch, FDEnvironmentError(
            f"`$timeout` — `{member.name}`'s highest role is not below the bot's role; move the bot's role higher."
        ))
        return

    author_name = getattr(author, "name", "unknown")
    full_reason = f"{reason} (via $timeout by {author_name})" if reason else f"FDScript timeout invoked by {author_name}"

    try:
        await member.timeout(datetime.timedelta(seconds=seconds), reason=full_reason[:512])
        ctx.log_event(f"timeout → timed out {member.name} ({user_id}) for {seconds}s")
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            f"`$timeout` — bot lacks permission to timeout `{member.name}`. "
            "Ensure the bot has 'Moderate Members' permission and its highest role is above the target user."
        ))
    except discord.HTTPException as ex:
        ctx.log_event(f"timeout → ✗ HTTP error {ex.status}: {ex.text}")
        await _send_error(ch, FDRuntimeError(f"`$timeout` — Discord API error: `{ex.text}`"))