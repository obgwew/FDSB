# cmds_FDScripts/returnGetReactions.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDRuntimeError, FDEnvironmentError,
    _send_error, _parse_separator,
)

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) != 6:
        await _send_error(ch, FDLogicError(
            "`$returnGetReactions` requires 6 arguments:\n"
            "`$returnGetReactions[channelID; messageID; type; var; separator; emoji]`"
        ))
        return

    resolved = [ctx.resolve(arg).strip() for arg in args]
    
    ch_id_str  = resolved[0]
    msg_id_str = resolved[1]
    type_str   = resolved[2].lower()
    var_name   = resolved[3]
    separator  = _parse_separator(resolved[4])
    emoji_raw  = resolved[5]

    if not ch_id_str.isdigit() or not msg_id_str.isdigit():
        await _send_error(ch, FDLogicError(
            "`$returnGetReactions` — channelID and messageID must be integers"
        ))
        return

    if type_str not in ("usersid", "tr"):
        await _send_error(ch, FDLogicError(
            f"`$returnGetReactions` — unknown type `{type_str}`.\n"
            f"Valid types are: `usersID` or `tr` (total reactions)."
        ))
        return

    if not var_name:
        await _send_error(ch, FDLogicError(
            "`$returnGetReactions` — variable name cannot be empty"
        ))
        return

    target_ch = ctx.bot.get_channel(int(ch_id_str))
    if not target_ch:
        await _send_error(ch, FDEnvironmentError(
            f"`$returnGetReactions` — channel `{ch_id_str}` not found or bot has no access"
        ))
        return

    try:
        target_msg = await target_ch.fetch_message(int(msg_id_str))
    except discord.NotFound:
        await _send_error(ch, FDEnvironmentError(
            f"`$returnGetReactions` — message `{msg_id_str}` not found in channel `{ch_id_str}`"
        ))
        return
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$returnGetReactions` — bot lacks `Read Message History` permission in that channel"
        ))
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDRuntimeError(
            f"`$returnGetReactions` — failed to fetch message: `{e.text}`"
        ))
        return

    matched_reaction: discord.Reaction | None = None
    for reaction in target_msg.reactions:
        r_emoji = str(reaction.emoji)
        if r_emoji == emoji_raw:
            matched_reaction = reaction
            break
        if hasattr(reaction.emoji, 'name') and reaction.emoji.name == emoji_raw:
            matched_reaction = reaction
            break

    if matched_reaction is None:
        if type_str == "tr":
            ctx.return_vars[var_name] = "0"
            ctx.log_event(f"returnGetReactions [{emoji_raw}] → 0 reactions stored in `{var_name}`")
            return
        else:
            await _send_error(ch, FDRuntimeError(
                f"`$returnGetReactions` — emoji `{emoji_raw}` was not found on message `{msg_id_str}`"
            ))
            return

    try:
        users = [u async for u in matched_reaction.users() if not u.bot]
    except discord.HTTPException as e:
        await _send_error(ch, FDRuntimeError(
            f"`$returnGetReactions` — failed to fetch reaction users: `{e.text}`"
        ))
        return

    if type_str == "tr":
        result = str(len(users))
    else:
        if not users:
            await _send_error(ch, FDRuntimeError(
                f"`$returnGetReactions` — no human users reacted with `{emoji_raw}` on message `{msg_id_str}`"
            ))
            return
        result = separator.join(str(u.id) for u in users)

    ctx.return_vars[var_name] = result
    ctx.log_event(f"returnGetReactions [{emoji_raw} ({type_str})] → stored in `{var_name}`")