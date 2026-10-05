# cmds_FDScripts/userBanner.py
import re, json, time, urllib.request
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError, _send_error,
)

_CACHE: dict[int, tuple[float, str | None]] = {}
_TTL = 300


def _banner_url(user_id: int, banner_hash: str | None) -> str | None:
    if not banner_hash:
        return None
    ext = "gif" if banner_hash.startswith("a_") else "png"
    return f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{ext}"


def _fetch_sync(user_id: int, ctx: ExecutionContext) -> str | None:
    cached = _CACHE.get(user_id)
    if cached and time.time() - cached[0] < _TTL:
        return cached[1]

    req = urllib.request.Request(
        f"https://discord.com/api/v10/users/{user_id}",
        headers={
            "Authorization": f"Bot {ctx.bot.http.token}",
            "User-Agent": "DiscordBot (FDScript, 1.0)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.load(r)
    except Exception:
        return None

    url = _banner_url(user_id, data.get("banner"))
    _CACHE[user_id] = (time.time(), url)
    return url


def _parse_id(args, ctx):
    raw = ctx.resolve(args[0]).strip() if args and args[0].strip() else str(ctx.bot.user.id)
    digits = re.sub(r"\D", "", raw)
    return (int(digits), raw) if digits else (None, raw)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    fallback = ctx.resolve(args[1]).strip() if len(args) > 1 else ""

    if not ctx.bot or not ctx.bot.user:
        return fallback

    user_id, _ = _parse_id(args, ctx)
    if user_id is None:
        return fallback

    return _fetch_sync(user_id, ctx) or fallback


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not ctx.bot or not ctx.bot.user:
        await _send_error(ch, FDEnvironmentError("`$userBanner` — bot user is not ready or unavailable"))
        return

    user_id, raw = _parse_id(args, ctx)
    if user_id is None:
        await _send_error(ch, FDLogicError(f"`$userBanner` — invalid user ID (got `{raw}`)"))
        return

    try:
        user = await ctx.bot.fetch_user(user_id)
    except (discord.NotFound, discord.HTTPException):
        await _send_error(ch, FDLogicError(f"`$userBanner` — no user found with ID `{user_id}`"))
        return

    if user.banner is None:
        await _send_error(ch, FDLogicError(f"`$userBanner` — user `{user.name}` has no banner set"))
        return

    url = _banner_url(user_id, user.banner.key)
    ctx.stop_typing()
    dest = await ctx.get_dest()
    ctx.last_bot_message = await dest.send(url)
    ctx.log_event(f"userBanner → {url} (user {user.id})")