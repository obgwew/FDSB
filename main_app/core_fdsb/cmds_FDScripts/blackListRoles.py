# cmds_FDScripts/blackListRoles.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error
from engine_FDScript import blacklist_ops as bl


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args or not args[0].strip():
        await _send_error(ch, FDLogicError(
            "`$blackListRoles` requires at least one role — "
            "example: `$blackListRoles[roleID/rolename; ...; Custom Error Message]`"
        ))
        return

    targets, custom_error = bl.parse_blacklist_args(args, ctx)
    if not targets:
        await _send_error(ch, FDLogicError("`$blackListRoles` — target role cannot be empty."))
        return

    author = ctx.interaction.user if ctx.interaction else (ctx.message.author if ctx.message else None)
    guild = ctx.interaction.guild if ctx.interaction else (ctx.message.guild if ctx.message else None)

    member = author
    if guild and author and not isinstance(author, discord.Member):
        member = guild.get_member(author.id)

    is_blocked, matched_info = bl.check_role_blocked(targets, member)

    default_err = f"`$blackListRoles` — You possess the blacklisted role: `{matched_info}`."
    await bl.enforce_blacklist(
        cmd_name="blackListRoles",
        is_blocked=is_blocked,
        matched_info=matched_info,
        custom_error=custom_error,
        ctx=ctx,
        default_err_text=default_err,
    )