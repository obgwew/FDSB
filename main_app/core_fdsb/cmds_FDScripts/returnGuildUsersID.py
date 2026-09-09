# cmds_FDScripts/returnGuildUsersID.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDRuntimeError, FDEnvironmentError,
    _send_error, _parse_separator,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved = [ctx.resolve(arg).strip() for arg in args if arg.strip()]

    if len(resolved) != 4:
        await _send_error(ch, FDLogicError(
            "`$returnGuildUsersID` requires 4 arguments:\n"
            "`$returnGuildUsersID[guildID; cache/chunk; var; separator]`"
        ))
        return

    guild_id_str = resolved[0]
    fetch_mode   = resolved[1].lower()
    var_name     = resolved[2]
    separator    = _parse_separator(resolved[3])

    if not guild_id_str or not guild_id_str.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$returnGuildUsersID` — invalid guild ID: `{guild_id_str}`"
        ))
        return

    if fetch_mode not in ("cache", "chunk"):
        await _send_error(ch, FDLogicError(
            f"`$returnGuildUsersID` — fetch mode must be `cache` or `chunk`, got: `{fetch_mode}`"
        ))
        return

    if not var_name:
        await _send_error(ch, FDLogicError(
            "`$returnGuildUsersID` — variable name cannot be empty"
        ))
        return

    guild = ctx.bot.get_guild(int(guild_id_str))
    if not guild:
        await _send_error(ch, FDEnvironmentError(
            f"`$returnGuildUsersID` — guild `{guild_id_str}` not found or bot is not in it"
        ))
        return

    if fetch_mode == "chunk":
        try:
            await guild.chunk()
        except discord.HTTPException as e:
            await _send_error(ch, FDRuntimeError(
                f"`$returnGuildUsersID` — failed to chunk guild: `{e.text}`"
            ))
            return

    members = [m for m in guild.members if not m.bot]
    if not members:
        await _send_error(ch, FDRuntimeError(
            f"`$returnGuildUsersID` — no human members found in guild `{guild_id_str}`"
        ))
        return

    ctx.return_vars[var_name] = separator.join(str(m.id) for m in members)
    ctx.log_event(
        f"returnGuildUsersID [{fetch_mode}] → {len(members)} member(s) stored in `{var_name}`"
    )