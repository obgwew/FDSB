# cmds_FDScripts/tts.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError,
    _send_error, _truncate,
)

_MAX_LEN = 2000


def _target_channel(ctx: ExecutionContext):
    if ctx._channel_override is not None:
        return ctx._channel_override
    if ctx.dm_target is not None:
        return None
    if ctx.interaction is not None:
        return ctx.interaction.channel
    return getattr(ctx.message, "channel", None)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args or not any(a.strip() for a in args):
        await _send_error(ch, FDSyntaxError("`$tts` — requires the text to speak: `$tts[text]`"))
        return

    text = ";".join(ctx.resolve(a) for a in args).strip()

    if not text:
        await _send_error(ch, FDLogicError("`$tts` — the text is empty after resolving"))
        return

    if len(text) > _MAX_LEN:
        await _send_error(ch, FDLogicError(
            f"`$tts` — text is too long ({len(text)} chars; Discord's limit is {_MAX_LEN})"
        ))
        return

    target = _target_channel(ctx)
    guild = getattr(target, "guild", None)
    if guild is not None and guild.me is not None:
        if not target.permissions_for(guild.me).send_tts_messages:
            await _send_error(ch, FDEnvironmentError(
                "`$tts` — the bot lacks the `Send TTS Messages` permission in this channel."
            ))
            return

    ctx.stop_typing()
    dest = ch
    if ctx.sync_mode:
        dest = await ctx.get_dest(raw=True)
        ctx.log_event("tts → syncMode active; TTS message sent separately from the synced message")

    try:
        sent = await dest.send(text, tts=True)
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$tts` — the bot isn't allowed to send messages (or TTS messages) here."
        ))
        return
    except discord.HTTPException as e:
        ctx.log_event(f"warning: `$tts` failed to send: `{e.text}`")
        return

    if sent is None:  
        ctx.log_event("tts → text contained only links; nothing left to send")
        return
    ctx.log_event(f"tts → sent: {_truncate(text)!r}")