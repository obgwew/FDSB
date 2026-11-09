# cmds_FDScripts/editEmbedIn.py
import asyncio
import re

import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError,
    _send_error,
)
from engine_FDScript.parse_utils import _try_parse_color, _NAMED_COLORS
from engine_FDScript.embed_ops import build_edited_embeds, flush_pending_message

_USAGE = "`$editEmbedIn[time;(title);(description);(footer);(color)]`"
_TIME_RE = re.compile(r"(\d+)([smhd])", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _parse_delay(raw: str) -> int | None:
    m = _TIME_RE.fullmatch(raw)
    if m is None:
        return None
    return int(m.group(1)) * _UNIT_SECONDS[m.group(2).lower()]


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not 2 <= len(args) <= 5:
        await _send_error(ch, FDSyntaxError(
            f"`$editEmbedIn` — expected 2 to 5 arguments: {_USAGE} (got {len(args)})"
        ))
        return

    vals = [ctx.resolve(a).strip() for a in args]
    time_raw, title, description, footer, color_raw = (vals + [""] * 5)[:5]

    seconds = _parse_delay(time_raw)
    if seconds is None:
        await _send_error(ch, FDLogicError(
            f"`$editEmbedIn` — invalid time `{time_raw}` "
            "(a whole number followed by s, m, h or d — e.g. `30s`, `5m`, `2h`, `1d`)"
        ))
        return

    if not (title or description or footer or color_raw):
        await _send_error(ch, FDSyntaxError(
            "`$editEmbedIn` — nothing to change: give at least one of title, description, footer, color"
        ))
        return

    color = None
    if color_raw:
        color = _try_parse_color(color_raw)
        if color is None:
            await _send_error(ch, FDLogicError(
                f"`$editEmbedIn` — invalid color `{color_raw}` (use a hex value like `#ff0000` or a color name)\n"
                f"Named colors: {', '.join(sorted(_NAMED_COLORS))}"
            ))
            return

    await flush_pending_message(ctx, ch)

    target = ctx.last_bot_message
    if target is None:
        await _send_error(ch, FDLogicError(
            "`$editEmbedIn` — the bot has not sent any message in this script yet, so there is no embed to edit"
        ))
        return
    if getattr(target, "id", 0) == 0:
        await _send_error(ch, FDEnvironmentError(
            "`$editEmbedIn` — the last message is not a real Discord message yet (syncMode collects into one message)"
        ))
        return
    if not target.embeds:
        await _send_error(ch, FDLogicError(
            "`$editEmbedIn` — the last message the bot sent has no embed to edit"
        ))
        return

    ctx.log_event(f"editEmbedIn → waiting {time_raw} before editing message {target.id}")
    try:
        await asyncio.sleep(seconds)
    except OverflowError:
        await _send_error(ch, FDLogicError(f"`$editEmbedIn` — time `{time_raw}` is too large"))
        return

    embeds = build_edited_embeds(
        target,
        title=title or None,
        description=description or None,
        footer=footer or None,
        color=color,
    )

    try:
        edited = await target.edit(embeds=embeds)
    except discord.NotFound:
        await _send_error(ch, FDLogicError(
            f"`$editEmbedIn` — message `{target.id}` no longer exists (deleted while waiting)"
        ))
        return
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$editEmbedIn` — the bot cannot edit that message"
        ))
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDLogicError(f"`$editEmbedIn` — Discord rejected the edit: {e.text}"))
        return

    if edited is not None:
        ctx.last_bot_message = edited

    changed = [n for n, v in (("title", title), ("description", description),
                              ("footer", footer), ("color", color_raw)) if v]
    ctx.log_event(f"editEmbedIn → message {target.id} embed updated after {time_raw} ({', '.join(changed)})")