# cmds_FDScripts/getMessage.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError,
    _send_error,
)

_VALID_TYPES = {"content", "name", "avatar", "id"}


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 2:
        await _send_error(ch, FDSyntaxError(
            "`$getMessage` requires at least 2 arguments: "
            "`$getMessage[channelID; messageID; (type, optional)]`"
        ))
        return

    channel_id_arg = ctx.resolve(args[0]).strip()
    message_id_arg = ctx.resolve(args[1]).strip()
    type_arg = ctx.resolve(args[2]).strip().lower() if len(args) > 2 and args[2].strip() else "content"

    if not channel_id_arg.isdigit():
        await _send_error(ch, FDLogicError(
            "`$getMessage` — the channel ID (1st arg) must be a valid snowflake (numbers only)"
        ))
        return

    if not message_id_arg.isdigit():
        await _send_error(ch, FDLogicError(
            "`$getMessage` — the message ID (2nd arg) must be a valid snowflake (numbers only)"
        ))
        return

    if type_arg not in _VALID_TYPES:
        await _send_error(ch, FDLogicError(
            f"`$getMessage` — unknown type `{type_arg}`. "
            f"Valid types: name, avatar, id, content"
        ))
        return

    target_channel = ctx.bot.get_channel(int(channel_id_arg))
    if target_channel is None:
        try:
            target_channel = await ctx.bot.fetch_channel(int(channel_id_arg))
        except discord.NotFound:
            await _send_error(ch, FDLogicError(
                f"`$getMessage` — no channel found with ID `{channel_id_arg}`"
            ))
            return
        except discord.Forbidden:
            await _send_error(ch, FDEnvironmentError(
                "`$getMessage` — bot lacks permission to view that channel"
            ))
            return
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(
                f"`$getMessage` — failed to fetch channel `{channel_id_arg}`: `{e}`"
            ))
            return

    if not isinstance(target_channel, discord.abc.Messageable):
        await _send_error(ch, FDLogicError(
            f"`$getMessage` — channel `{channel_id_arg}` is not a text channel"
        ))
        return

    try:
        target_message = await target_channel.fetch_message(int(message_id_arg))
    except discord.NotFound:
        await _send_error(ch, FDLogicError(
            f"`$getMessage` — no message found with ID `{message_id_arg}` in that channel"
        ))
        return
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$getMessage` — bot lacks `Read Message History` permission in that channel"
        ))
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDLogicError(
            f"`$getMessage` — failed to fetch message `{message_id_arg}`: `{e}`"
        ))
        return

    if type_arg == "content":
        value = target_message.content or ""
    elif type_arg == "name":
        value = str(target_message.author.display_name)
    elif type_arg == "id":
        value = str(target_message.author.id)
    elif type_arg == "avatar":
        value = str(target_message.author.display_avatar.url)
    else:
        value = ""

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(value if value else "\u200b")
    ctx.last_bot_message = sent
    ctx.log_event(f"getMessage[{type_arg}] → {value}")