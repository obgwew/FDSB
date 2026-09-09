# cmds_FDScripts/isNSFW.py
import re
import discord

from FDScript import ExecutionContext, Command, FDLogicError, FDEnvironmentError, _send_error

_CHANNEL_MENTION_RE = re.compile(r'^<#(\d+)>$')


def _parse_channel_id(raw: str) -> int | None:
    raw = raw.strip()
    mention_match = _CHANNEL_MENTION_RE.match(raw)
    if mention_match:
        return int(mention_match.group(1))
    if raw.isdigit():
        return int(raw)
    return None


def _channel_is_nsfw(channel) -> bool:
    is_nsfw_fn = getattr(channel, "is_nsfw", None)
    if not callable(is_nsfw_fn):
        return False
    try:
        return bool(is_nsfw_fn())
    except TypeError:
        return False


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return ""

    raw = ctx.resolve(args[0]).strip()
    channel_id = _parse_channel_id(raw)
    if channel_id is None:
        return ""

    channel = ctx.bot.get_channel(channel_id)
    if channel is None:
        return ""

    return "true" if _channel_is_nsfw(channel) else "false"


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$isNSFW` requires a channel argument: `$isNSFW[channel id/mention]`"
        ))
        return

    raw = ctx.resolve(args[0]).strip()
    channel_id = _parse_channel_id(raw)

    if channel_id is None:
        await _send_error(ch, FDLogicError(
            f"`$isNSFW` — invalid channel: `{raw}`.\n"
            f"Use a channel ID or a mention (e.g. `<#123456789012345678>`)."
        ))
        return

    channel = ctx.bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await ctx.bot.fetch_channel(channel_id)
        except discord.NotFound:
            await _send_error(ch, FDEnvironmentError(
                f"`$isNSFW` — no channel found with ID `{channel_id}`"
            ))
            return
        except discord.Forbidden:
            await _send_error(ch, FDEnvironmentError(
                f"`$isNSFW` — bot lacks access to channel `{channel_id}`"
            ))
            return
        except discord.HTTPException as e:
            await _send_error(ch, FDEnvironmentError(
                f"`$isNSFW` — failed to fetch channel `{channel_id}`: `{e.text}`"
            ))
            return

    result = "true" if _channel_is_nsfw(channel) else "false"

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"isNSFW → {raw} => {result}")