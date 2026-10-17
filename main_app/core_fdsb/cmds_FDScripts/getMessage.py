# cmds_FDScripts/getMessage.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError,
    _send_error,
)

_VALID_TYPES = {"content", "name", "avatar", "id"}


def _store(ctx: ExecutionContext) -> dict:
    store = getattr(ctx, "_fetched_messages", None)
    if store is None:
        store = {}
        ctx._fetched_messages = store
    return store


def _extract_value(msg: discord.Message, type_arg: str) -> str:
    if type_arg == "content":
        return msg.content or ""
    if type_arg == "name":
        return str(msg.author.display_name)
    if type_arg == "id":
        return str(msg.author.id)
    if type_arg == "avatar":
        return str(msg.author.display_avatar.url)
    return ""


async def _load_message(args: list[str], ctx: ExecutionContext, ch):
    if len(args) < 2:
        await _send_error(ch, FDSyntaxError(
            "`$getMessage` requires at least 2 arguments: "
            "`$getMessage[channelID; messageID; (type, optional)]`"
        ))

    channel_id_arg = ctx.resolve(args[0]).strip()
    message_id_arg = ctx.resolve(args[1]).strip()
    type_arg = ctx.resolve(args[2]).strip().lower() if len(args) > 2 and args[2].strip() else "content"

    if not channel_id_arg.isdigit():
        await _send_error(ch, FDLogicError(
            "`$getMessage` — the channel ID (1st arg) must be a valid snowflake (numbers only)"
        ))
    if not message_id_arg.isdigit():
        await _send_error(ch, FDLogicError(
            "`$getMessage` — the message ID (2nd arg) must be a valid snowflake (numbers only)"
        ))
    if type_arg not in _VALID_TYPES:
        await _send_error(ch, FDLogicError(
            f"`$getMessage` — unknown type `{type_arg}`. Valid types: name, avatar, id, content"
        ))

    target_channel = ctx.bot.get_channel(int(channel_id_arg))
    if target_channel is None:
        try:
            target_channel = await ctx.bot.fetch_channel(int(channel_id_arg))
        except discord.NotFound:
            await _send_error(ch, FDLogicError(
                f"`$getMessage` — no channel found with ID `{channel_id_arg}`"
            ))
        except discord.Forbidden:
            await _send_error(ch, FDEnvironmentError(
                "`$getMessage` — bot lacks permission to view that channel"
            ))
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(
                f"`$getMessage` — failed to fetch channel `{channel_id_arg}`: `{e}`"
            ))

    if not isinstance(target_channel, discord.abc.Messageable):
        await _send_error(ch, FDLogicError(
            f"`$getMessage` — channel `{channel_id_arg}` is not a text channel"
        ))

    try:
        target_message = await target_channel.fetch_message(int(message_id_arg))
    except discord.NotFound:
        await _send_error(ch, FDLogicError(
            f"`$getMessage` — no message found with ID `{message_id_arg}` in that channel"
        ))
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$getMessage` — bot lacks `Read Message History` permission in that channel"
        ))
    except discord.HTTPException as e:
        await _send_error(ch, FDLogicError(
            f"`$getMessage` — failed to fetch message `{message_id_arg}`: `{e}`"
        ))

    return target_message, type_arg, (int(channel_id_arg), int(message_id_arg))


async def prefetch(args: list[str], ctx: ExecutionContext, ch) -> None:
    msg, _type, key = await _load_message(args, ctx, ch)
    _store(ctx)[key] = msg


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 2:
        ctx._abort_with_error(FDSyntaxError(
            "`$getMessage` requires at least 2 arguments: "
            "`$getMessage[channelID; messageID; (type, optional)]`"
        ))
    channel_id_arg = ctx.resolve(args[0]).strip()
    message_id_arg = ctx.resolve(args[1]).strip()
    type_arg = ctx.resolve(args[2]).strip().lower() if len(args) > 2 and args[2].strip() else "content"

    if not (channel_id_arg.isdigit() and message_id_arg.isdigit()) or type_arg not in _VALID_TYPES:
        ctx._abort_with_error(FDLogicError("`$getMessage` — invalid arguments"))

    msg = _store(ctx).get((int(channel_id_arg), int(message_id_arg)))
    if msg is None:
        ctx._abort_with_error(FDEnvironmentError(
            "`$getMessage` — message was not pre-fetched (internal: prefetch hook missing)"
        ))
    return _extract_value(msg, type_arg)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    target_message, type_arg, _key = await _load_message(args, ctx, ch)
    value = _extract_value(target_message, type_arg)

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(value if value else "\u200b")
    ctx.last_bot_message = sent
    ctx.log_event(f"getMessage[{type_arg}] → {value}")