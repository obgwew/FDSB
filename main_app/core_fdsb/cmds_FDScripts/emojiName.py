# cmds_FDScripts/emojiName.py
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


def _resolve_emoji_name(emoji_id_str: str, ctx: ExecutionContext) -> tuple[str | None, bool]:
    emoji_id = _extract_emoji_id(emoji_id_str)
    if emoji_id is None:
        return None, False

    emoji = ctx.bot.get_emoji(emoji_id)
    if emoji is None:
        return None, True

    return emoji.name, True


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return ""
    emoji_id_str = ctx.resolve(args[0]).strip()
    name, _ = _resolve_emoji_name(emoji_id_str, ctx)
    return name or ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$emojiName` requires 1 argument: $emojiName[emoji id]"
        ))
        return

    emoji_id_str = ctx.resolve(args[0]).strip()
    name, is_valid_id = _resolve_emoji_name(emoji_id_str, ctx)

    if name is None:
        if not is_valid_id:
            await _send_error(ch, FDLogicError(
                f"`$emojiName` — invalid emoji ID or format: `{emoji_id_str}`. "
                f"Expected a numeric ID or `<:name:id>` / `<a:name:id>`"
            ))
            return

        await _send_error(ch, FDLogicError(
            f"`$emojiName` — no emoji found with ID `{emoji_id_str}` "
            f"(bot must share a server with this emoji)"
        ))
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(name)
    ctx.last_bot_message = sent
    ctx.log_event(f"emojiName → {name!r} (id={emoji_id_str})")