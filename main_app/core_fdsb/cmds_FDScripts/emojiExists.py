# cmds_FDScripts/emojiExists.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error

_EMOJI_TAG_RE = re.compile(r"<a?:\w+:(\d+)>")


def _extract_emoji_id(raw: str) -> int | None:
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)

    match = _EMOJI_TAG_RE.fullmatch(raw)
    if match:
        return int(match.group(1))

    return None


def _emoji_exists(emoji_id_str: str, ctx: ExecutionContext) -> bool | None:
    emoji_id = _extract_emoji_id(emoji_id_str)
    if emoji_id is None:
        return None
    return ctx.bot.get_emoji(emoji_id) is not None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return "false"
    emoji_id_str = ctx.resolve(args[0]).strip()
    exists = _emoji_exists(emoji_id_str, ctx)
    return "true" if exists else "false"


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$emojiExists` requires 1 argument: $emojiExists[emoji id]"
        ))
        return

    emoji_id_str = ctx.resolve(args[0]).strip()
    exists = _emoji_exists(emoji_id_str, ctx)

    if exists is None:
        await _send_error(ch, FDLogicError(
            f"`$emojiExists` — invalid emoji ID or format: `{emoji_id_str}`. "
            f"Expected a numeric ID or `<:name:id>` / `<a:name:id>`"
        ))
        return

    result = "true" if exists else "false"
    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"emojiExists → {result} (id={emoji_id_str})")