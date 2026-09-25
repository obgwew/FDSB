# cmds_FDScripts/clientBanner.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error,
)


def _format_banner(asset: discord.Asset) -> str:
    fmt = "gif" if asset.is_animated() else "png"
    return asset.with_format(fmt).url


def _get_cached_banner(user_id: int, ctx: ExecutionContext) -> str | None:
    user = ctx.bot.get_user(user_id)
    if user and getattr(user, "banner", None):
        return _format_banner(user.banner)
    return None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not ctx.bot or not ctx.bot.user:
        return ""

    raw_id = ctx.resolve(args[0]).strip() if args and args[0].strip() else str(ctx.bot.user.id)
    clean_id = re.sub(r"\D", "", raw_id)

    if not clean_id.isdigit():
        return ""

    user_id = int(clean_id)
    return _get_cached_banner(user_id, ctx) or ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not ctx.bot or not ctx.bot.user:
        await _send_error(ch, FDEnvironmentError("`$clientBanner` — bot user is not ready or unavailable"))
        return

    raw_id = ctx.resolve(args[0]).strip() if args and args[0].strip() else str(ctx.bot.user.id)
    clean_id = re.sub(r"\D", "", raw_id)

    if not clean_id.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$clientBanner` — user ID or mention must be a numeric snowflake (got `{raw_id}`)"
        ))
        return

    user_id = int(clean_id)

    try:
        user = await ctx.bot.fetch_user(user_id)
    except (discord.NotFound, discord.HTTPException):
        await _send_error(ch, FDLogicError(
            f"`$clientBanner` — no user found with ID `{user_id}`"
        ))
        return

    if getattr(user, "banner", None) is None:
        await _send_error(ch, FDLogicError(
            f"`$clientBanner` — user `{user.name}` has no banner set"
        ))
        return

    url = _format_banner(user.banner)

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(url)
    ctx.last_bot_message = sent
    ctx.log_event(f"clientBanner → {url} (user {user.id})")