# cmds_FDScripts/boostCount.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error,
)


def _resolve_guild(ctx: ExecutionContext, guild_id_raw: str | None) -> discord.Guild | None:
    if guild_id_raw:
        guild_id_raw = guild_id_raw.strip()
        if not guild_id_raw.isdigit():
            return None
        return ctx.bot.get_guild(int(guild_id_raw))

    if getattr(ctx, "message", None) is not None and ctx.message.guild is not None:
        return ctx.message.guild
    if getattr(ctx, "interaction", None) is not None and ctx.interaction.guild is not None:
        return ctx.interaction.guild
    return None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    guild_id = None
    if args:
        guild_id = ctx.resolve(args[0]).strip()
        if not guild_id:
            guild_id = None

    guild = _resolve_guild(ctx, guild_id)
    if guild is None:
        return "0"
    return str(guild.premium_subscription_count or 0)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild_id = None
    if args:
        guild_id = ctx.resolve(args[0]).strip()
        if not guild_id:
            guild_id = None

    if guild_id is not None and not guild_id.isdigit():
        await _send_error(ch, FDLogicError(
            "`$boostCount` — guild ID must be a numeric snowflake "
            f"(got `{guild_id}`)"
        ))
        return

    guild = _resolve_guild(ctx, guild_id)
    if guild is None:
        if guild_id:
            await _send_error(ch, FDEnvironmentError(
                f"`$boostCount` — guild `{guild_id}` not found "
                f"(bot may not be a member of that server)"
            ))
        else:
            await _send_error(ch, FDEnvironmentError(
                "`$boostCount` — no guild available in this context "
                "(cannot be used in DMs without a guild ID)"
            ))
        return

    value = str(guild.premium_subscription_count or 0)

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(value)
    ctx.last_bot_message = sent
    ctx.log_event(f"boostCount → {value} (guild {guild.id})")
