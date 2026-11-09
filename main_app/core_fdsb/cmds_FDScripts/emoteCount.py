# cmds_FDScripts/emoteCount.py
from FDScript import ExecutionContext, FDLogicError, FDEnvironmentError


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    raw = ";".join(args).strip()
    guild_id = raw if raw else str(ctx.builtins.get("guildID", ""))

    if not guild_id.isdigit():
        if raw:
            ctx._abort_with_error(FDLogicError(
                f"`$emoteCount` — guild ID must be a numeric snowflake (got `{raw}`)"
            ))
        ctx._abort_with_error(FDEnvironmentError(
            "`$emoteCount` — no server in this context (DM): pass a guild ID, `$emoteCount[guildID]`"
        ))

    guild = ctx.bot.get_guild(int(guild_id))
    if guild is None:
        ctx._abort_with_error(FDEnvironmentError(
            f"`$emoteCount` — server `{guild_id}` not found (the bot isn't in it)"
        ))

    count = len(guild.emojis)
    ctx.log_event(f"emoteCount → {count} (guild {guild.id})")
    return str(count)