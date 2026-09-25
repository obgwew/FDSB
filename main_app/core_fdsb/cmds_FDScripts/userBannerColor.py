# cmds_FDScripts/userBannerColor.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error,
)


def _format_hex(color: discord.Color) -> str:
    return f"#{color.value:06X}"


def _get_cached_color(user_id: int, ctx: ExecutionContext) -> str | None:
    user = ctx.bot.get_user(user_id)
    if user and getattr(user, "accent_color", None):
        return _format_hex(user.accent_color)
    return None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not ctx.bot or not ctx.bot.user:
        return ""

    raw_id = ctx.resolve(args[0]).strip() if args and args[0].strip() else str(ctx.bot.user.id)
    clean_id = re.sub(r"\D", "", raw_id)

    if not clean_id.isdigit():
        return ""

    user_id = int(clean_id)
    return _get_cached_color(user_id, ctx) or ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not ctx.bot or not ctx.bot.user:
        await _send_error(ch, FDEnvironmentError("`$clientBannerColor` — bot user is not ready or unavailable"))
        return

    raw_id = ctx.resolve(args[0]).strip() if args and args[0].strip() else str(ctx.bot.user.id)
    clean_id = re.sub(r"\D", "", raw_id)

    if not clean_id.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$clientBannerColor` — user ID or mention must be a numeric snowflake (got `{raw_id}`)"
        ))
        return

    user_id = int(clean_id)

    try:
        user = await ctx.bot.fetch_user(user_id)
    except (discord.NotFound, discord.HTTPException):
        await _send_error(ch, FDLogicError(
            f"`$clientBannerColor` — no user found with ID `{user_id}`"
        ))
        return

    if getattr(user, "accent_color", None) is None:
        await _send_error(ch, FDLogicError(
            f"`$clientBannerColor` — user `{user.name}` has no banner color or accent color set"
        ))
        return

    hex_color = _format_hex(user.accent_color)

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(hex_color)
    ctx.last_bot_message = sent
    ctx.log_event(f"clientBannerColor → {hex_color} (user {user.id})")