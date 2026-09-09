# cmds_FDScripts/addBotReactions.py
import asyncio
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error, _extract_all_emojis,
    _REACTIONS_MAX,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def _resolve_target_message(ctx: ExecutionContext, base_msg: discord.Message) -> discord.Message:
    override_channel = getattr(ctx, "_channel_override", None)
    if override_channel is None:
        return base_msg
    if getattr(base_msg.channel, "id", None) == override_channel.id:
        return base_msg
    try:
        return await override_channel.fetch_message(base_msg.id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return base_msg


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError("`$addBotReactions` requires at least one emoji argument"))
        return

    if ctx.last_bot_message is None:
        await _send_error(ch, FDEnvironmentError("`$addBotReactions` — no bot message was sent yet in this script execution"))
        return

    resolved_text = "".join(ctx.resolve(arg) for arg in args)
    emojis_to_add = _extract_all_emojis(resolved_text)

    if not emojis_to_add:
        await _send_error(ch, FDLogicError("`$addBotReactions` — no valid emojis found in input"))
        return

    if len(emojis_to_add) > _REACTIONS_MAX:
        await _send_error(ch, FDLogicError(f"Too many emojis (max {_REACTIONS_MAX})"))
        return

    target_msg: discord.Message = await _resolve_target_message(ctx, ctx.last_bot_message)
    added: int = 0
    errors: list[str] = []

    for emoji in emojis_to_add:
        try:
            await target_msg.add_reaction(emoji)
            added += 1
            await asyncio.sleep(0.35)
        except discord.Forbidden:
            await _send_error(ch, FDEnvironmentError("Bot lacks `Add Reactions` permission in this channel"))
            return
        except discord.HTTPException as e:
            if e.status == 429:
                retry = getattr(e, "retry_after", 1.5)
                await asyncio.sleep(retry)
                try:
                    await target_msg.add_reaction(emoji)
                    added += 1
                except Exception as e2:
                    errors.append(f"`{emoji}` retry failed: {e2}")
                    continue
            elif e.status == 400:
                errors.append(f"`{emoji}` emoji not available to bot (maybe custom emoji from another server?)")
                continue
            else:
                errors.append(f"`{emoji}` HTTP {e.status}: {e.text}")
                continue
        except Exception as ex:
            errors.append(f"`{emoji}` unexpected: {ex}")
            continue

    if errors:
        error_msg = "Some reactions failed:\n" + "\n".join(errors)
        await _send_error(ch, FDEnvironmentError(error_msg))
    else:
        ctx.log_event(f"addBotReactions → added {added} reaction(s)")