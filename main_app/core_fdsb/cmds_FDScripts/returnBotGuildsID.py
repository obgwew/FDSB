# cmds_FDScripts/returnBotGuildsID.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDRuntimeError,
    _send_error, _parse_separator,
)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved = [ctx.resolve(arg).strip() for arg in args]

    if len(resolved) != 3:
        await _send_error(ch, FDLogicError(
            "`$returnBotGuildsID` requires 3 arguments:\n"
            "`$returnBotGuildsID[cache/chunk; var; separator]`"
        ))
        return

    fetch_mode = resolved[0].lower()
    var_name   = resolved[1]
    separator  = _parse_separator(resolved[2])

    if fetch_mode not in ("cache", "chunk"):
        await _send_error(ch, FDLogicError(
            f"`$returnBotGuildsID` — fetch mode must be `cache` or `chunk`, got: `{fetch_mode}`"
        ))
        return

    if not var_name:
        await _send_error(ch, FDLogicError(
            "`$returnBotGuildsID` — variable name cannot be empty"
        ))
        return

    if fetch_mode == "chunk":
        try:
            guild_ids = [str(g.id) async for g in ctx.bot.fetch_guilds(limit=None)]
        except discord.HTTPException as e:
            await _send_error(ch, FDRuntimeError(
                f"`$returnBotGuildsID` — failed to fetch guilds: `{e.text}`"
            ))
            return
    else:
        guild_ids = [str(g.id) for g in ctx.bot.guilds]

    if not guild_ids:
        await _send_error(ch, FDRuntimeError(
            "`$returnBotGuildsID` — the bot is not in any guild"
        ))
        return

    ctx.return_vars[var_name] = separator.join(guild_ids)
    ctx.log_event(
        f"returnBotGuildsID [{fetch_mode}] → {len(guild_ids)} guild(s) stored in `{var_name}`"
    )