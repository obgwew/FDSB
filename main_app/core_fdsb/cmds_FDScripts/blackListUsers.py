# cmds_FDScripts/blackListUsers.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error
from engine_FDScript import blacklist_ops as bl


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args or not args[0].strip():
        await _send_error(ch, FDLogicError(
            "`$blackListUsers` requires at least one user — "
            "example: `$blackListUsers[userID/username; ...; Custom Error Message]`"
        ))
        return

    targets, custom_error = bl.parse_blacklist_args(args, ctx)
    if not targets:
        await _send_error(ch, FDLogicError("`$blackListUsers` — target user cannot be empty."))
        return

    author = ctx.interaction.user if ctx.interaction else (ctx.message.author if ctx.message else None)
    is_blocked, matched_info = bl.check_user_blocked(targets, author)

    default_err = f"`$blackListUsers` — You ({matched_info}) are blacklisted from using this command."
    await bl.enforce_blacklist(
        cmd_name="blackListUsers",
        is_blocked=is_blocked,
        matched_info=matched_info,
        custom_error=custom_error,
        ctx=ctx,
        default_err_text=default_err,
    )