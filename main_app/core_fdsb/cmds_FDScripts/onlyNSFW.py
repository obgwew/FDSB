# cmds_FDScripts/onlyNSFW.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDAbortScript, _send_error
)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    message = ";".join(ctx.resolve(a) for a in args).strip() if args else ""
    if not message:
        await _send_error(ch, FDSyntaxError(
            "`$onlyNSFW` requires an error message — example: `$onlyNSFW[Error message]`"
        ))
        return

    src = ctx.interaction or ctx.message
    channel = getattr(src, "channel", None)
    if isinstance(channel, discord.PartialMessageable) and ctx.bot:
        channel = ctx.bot.get_channel(channel.id) or channel

    is_nsfw = getattr(channel, "is_nsfw", None)
    if callable(is_nsfw) and is_nsfw():
        ctx.log_event("onlyNSFW → Passed.")
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(message)
    if sent:
        ctx.last_bot_message = sent
    ctx.log_event("onlyNSFW → Denied. Error message sent.")
    raise FDAbortScript()