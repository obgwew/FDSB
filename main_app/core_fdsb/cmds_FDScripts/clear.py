# cmds_FDScripts/clear.py

import re
from datetime import timedelta

import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDRuntimeError, FDEnvironmentError,
    _send_error, _CLEAR_DEFAULT, _CLEAR_MAX,
)

_SCAN_CAP   = 200
_BULK_AGE   = timedelta(days=14) - timedelta(minutes=5)
_USER_RE    = re.compile(r'^(?:<@!?(\d{15,25})>|(\d{15,25}))$')
_TRUE_WORDS  = {"true", "yes", "1", "on"}
_FALSE_WORDS = {"false", "no", "0", "off"}


def _target_channel(ctx: ExecutionContext):
    override = getattr(ctx, "_channel_override", None)
    if override is not None:
        return override
    if ctx.interaction is not None:
        return ctx.interaction.channel
    return ctx.message.channel if ctx.message is not None else None


def _trigger_anchor(ctx: ExecutionContext, channel):
    if ctx.interaction is not None or ctx.message is None:
        return None
    mid = getattr(ctx.message, "id", 0)
    if not mid or getattr(ctx.message.channel, "id", None) != getattr(channel, "id", None):
        return None
    return discord.Object(id=mid)


async def _delete_messages(channel, msgs: list) -> int:
    cutoff = discord.utils.utcnow() - _BULK_AGE
    recent = [m for m in msgs if m.created_at > cutoff]
    old    = [m for m in msgs if m.created_at <= cutoff]
    done = 0

    for i in range(0, len(recent), 100):
        chunk = recent[i:i + 100]
        if len(chunk) == 1:
            await chunk[0].delete()
        else:
            await channel.delete_messages(chunk)
        done += len(chunk)

    for m in old:
        try:
            await m.delete()
            done += 1
        except discord.NotFound:
            pass
    return done


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) > 3:
        await _send_error(ch, FDSyntaxError(
            f"`$clear` — takes at most 3 arguments `$clear[Amount;user id;remove pinned]`, got {len(args)}"
        ))
        return

    raw = [ctx.resolve(a).strip() for a in args] + [""] * (3 - len(args))
    raw_amount, raw_user, raw_pinned = raw

    # ── Amount ───────────────────────────────────────────────
    if not raw_amount:
        amount = _CLEAR_DEFAULT
    else:
        if not re.fullmatch(r"-?\d+", raw_amount):
            await _send_error(ch, FDLogicError(
                f"`$clear` — expected an integer between `1` and `{_CLEAR_MAX}`, got: `{raw_amount}`"
            ))
            return
        amount = int(raw_amount)
        if amount < 1:
            await _send_error(ch, FDLogicError(
                f"`$clear` — amount must be at least `1`, got: `{amount}`"
            ))
            return
        if amount > _CLEAR_MAX:
            await _send_error(ch, FDLogicError(
                f"`$clear` — amount `{amount}` exceeds the maximum allowed (`{_CLEAR_MAX}`)"
            ))
            return

    # ── User id (optional) ───────────────────────────────────
    user_id = None
    if raw_user:
        m = _USER_RE.match(raw_user)
        if not m:
            await _send_error(ch, FDLogicError(
                f"`$clear` — invalid user ID or mention: `{raw_user}`"
            ))
            return
        user_id = int(m.group(1) or m.group(2))

    # ── Remove pinned (optional, default: keep pinned) ───────
    remove_pinned = False
    if raw_pinned:
        word = raw_pinned.lower()
        if word in _TRUE_WORDS:
            remove_pinned = True
        elif word in _FALSE_WORDS:
            remove_pinned = False
        else:
            await _send_error(ch, FDLogicError(
                f"`$clear` — `remove pinned` must be `true` or `false`, got: `{raw_pinned}`"
            ))
            return

    # ── Channel & permissions ────────────────────────────────
    channel = _target_channel(ctx)
    guild   = getattr(channel, "guild", None)
    if channel is None or guild is None or not hasattr(channel, "delete_messages"):
        await _send_error(ch, FDEnvironmentError(
            "`$clear` — can only be used in a server channel (not in DMs)"
        ))
        return

    perms = channel.permissions_for(guild.me)
    if not perms.manage_messages or not perms.read_message_history:
        await _send_error(ch, FDEnvironmentError(
            "`$clear` — bot needs `Manage Messages` and `Read Message History` in this channel"
        ))
        return

    # ── Collect exactly `amount` matching messages, then delete ──
    try:
        found = []
        async for msg in channel.history(limit=_SCAN_CAP, before=_trigger_anchor(ctx, channel)):
            if user_id is not None and msg.author.id != user_id:
                continue
            if msg.pinned and not remove_pinned:
                continue
            found.append(msg)
            if len(found) >= amount:
                break
        deleted = await _delete_messages(channel, found) if found else 0
    except discord.Forbidden:
        ctx.log_event("clear → ✗ no permission")
        await _send_error(ch, FDEnvironmentError(
            "`$clear` — bot lacks `Manage Messages` permission in this channel"
        ))
        return
    except discord.HTTPException as e:
        ctx.log_event(f"clear → ✗ HTTP error: {e.status}")
        await _send_error(ch, FDRuntimeError(
            f"`$clear` — Discord API error: `{e.text}`"
        ))
        return

    scope = f"user {user_id}" if user_id is not None else "everyone"
    pins  = "pinned included" if remove_pinned else "pinned kept"
    ctx.log_event(f"clear [{amount}; {scope}; {pins}] → deleted {deleted} message(s)")