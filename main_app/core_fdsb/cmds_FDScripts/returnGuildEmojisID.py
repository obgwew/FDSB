# cmds_FDScripts/returnGuildEmojisID.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDRuntimeError, FDEnvironmentError,
    _send_error, _parse_separator,
)

_EMOJI_TYPES = {"all", "static", "animated"}


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved = [ctx.resolve(arg).strip() for arg in args]

    if len(resolved) != 4:
        await _send_error(ch, FDLogicError(
            "`$returnGuildEmojisID` requires 4 arguments:\n"
            "`$returnGuildEmojisID[GuildID; type; var; separator]`\n"
            "Leave type empty or use `all` to get all emojis.\n"
            f"Valid types: {', '.join(sorted(_EMOJI_TYPES))}"
        ))
        return

    guild_id_str = resolved[0]
    type_raw     = resolved[1].lower() or "all"
    var_name     = resolved[2]
    separator    = _parse_separator(resolved[3])

    if not guild_id_str or not guild_id_str.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$returnGuildEmojisID` — invalid guild ID: `{guild_id_str}`"
        ))
        return

    if type_raw not in _EMOJI_TYPES:
        await _send_error(ch, FDLogicError(
            f"`$returnGuildEmojisID` — unknown emoji type: `{type_raw}`\n"
            f"Valid types: {', '.join(sorted(_EMOJI_TYPES))}"
        ))
        return

    if not var_name:
        await _send_error(ch, FDLogicError(
            "`$returnGuildEmojisID` — variable name cannot be empty"
        ))
        return

    guild = ctx.bot.get_guild(int(guild_id_str))
    if not guild:
        await _send_error(ch, FDEnvironmentError(
            f"`$returnGuildEmojisID` — guild `{guild_id_str}` not found or bot is not in it"
        ))
        return

    if type_raw == "static":
        emojis = [e for e in guild.emojis if not e.animated]
    elif type_raw == "animated":
        emojis = [e for e in guild.emojis if e.animated]
    else:
        emojis = list(guild.emojis)

    if not emojis:
        await _send_error(ch, FDRuntimeError(
            f"`$returnGuildEmojisID` — no `{type_raw}` emojis found in guild `{guild_id_str}`"
        ))
        return

    ctx.return_vars[var_name] = separator.join(str(e.id) for e in emojis)
    ctx.log_event(
        f"returnGuildEmojisID [{type_raw}] → {len(emojis)} emoji(s) stored in `{var_name}`"
    )