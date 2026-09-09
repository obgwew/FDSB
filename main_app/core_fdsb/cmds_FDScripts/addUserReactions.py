# cmds_FDScripts/addUserReactions.py
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
        await _send_error(ch, FDLogicError(
            "`$addUserReactions` requires at least one emoji argument"
        ))
        return

    resolved_text = "".join(ctx.resolve(arg) for arg in args)
    emojis_to_add = _extract_all_emojis(resolved_text)

    if not emojis_to_add:
        ctx.log_event("warning: no valid emojis found in $addUserReactions")
        return

    if len(emojis_to_add) > _REACTIONS_MAX:
        await _send_error(ch, FDLogicError(
            f"`$addUserReactions` — too many emojis found: `{len(emojis_to_add)}`. "
            f"Maximum allowed is `{_REACTIONS_MAX}`."
        ))
        return

    target_msg: discord.Message = await _resolve_target_message(ctx, ctx.message)
    added: int = 0

    for emoji in emojis_to_add:
        try:
            await target_msg.add_reaction(emoji)
            added += 1
            await asyncio.sleep(0.35)
        except discord.HTTPException as e:
            if e.status == 429:
                retry = getattr(e, "retry_after", 1.0)
                await asyncio.sleep(retry)
                try:
                    await target_msg.add_reaction(emoji)
                    added += 1
                except Exception as e2:
                    ctx.log_event(f"warning: failed to add emoji `{emoji}` after retry: `{e2}`")
                    continue
            elif e.status == 400:
                ctx.log_event(f"warning: skipped unsupported emoji: `{emoji}`")
                continue
            else:
                ctx.log_event(f"warning: failed to add emoji `{emoji}`: `{e.text}`")
                continue
        except discord.Forbidden:
            await _send_error(ch, FDEnvironmentError(
                "`$addUserReactions` — bot lacks `Add Reactions` permission in this channel"
            ))
            return
        except Exception as ex:
            ctx.log_event(f"warning: unexpected error with emoji `{emoji}`: `{ex}`")
            continue

    ctx.log_event(f"addUserReactions → added {added} reaction(s) to user message")