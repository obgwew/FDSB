# cmds_FDScripts/returnGuildBansID.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDRuntimeError, FDEnvironmentError,
    _send_error, _parse_separator,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved = [ctx.resolve(arg).strip() for arg in args]

    if len(resolved) != 3:
        await _send_error(ch, FDLogicError(
            "`$returnGuildBansID` requires 3 arguments:\n"
            "`$returnGuildBansID[GuildID; var; separator]`"
        ))
        return

    guild_id_str = resolved[0]
    var_name     = resolved[1]
    separator    = _parse_separator(resolved[2])

    if not guild_id_str or not guild_id_str.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$returnGuildBansID` — invalid guild ID: `{guild_id_str}`"
        ))
        return

    if not var_name:
        await _send_error(ch, FDLogicError(
            "`$returnGuildBansID` — variable name cannot be empty"
        ))
        return

    guild = ctx.bot.get_guild(int(guild_id_str))
    if not guild:
        await _send_error(ch, FDEnvironmentError(
            f"`$returnGuildBansID` — guild `{guild_id_str}` not found or bot is not in it"
        ))
        return

    try:
        banned_ids = [str(entry.user.id) async for entry in guild.bans(limit=None)]
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            f"`$returnGuildBansID` — bot lacks `Ban Members` permission in guild `{guild_id_str}`"
        ))
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDRuntimeError(
            f"`$returnGuildBansID` — failed to fetch bans: `{e.text}`"
        ))
        return

    if not banned_ids:
        await _send_error(ch, FDRuntimeError(
            f"`$returnGuildBansID` — no banned users found in guild `{guild_id_str}`"
        ))
        return

    ctx.return_vars[var_name] = separator.join(banned_ids)
    ctx.log_event(
        f"returnGuildBansID → {len(banned_ids)} ban(s) stored in `{var_name}`"
    )