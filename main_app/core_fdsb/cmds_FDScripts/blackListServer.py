# cmds_FDScripts/blackListServer.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error
from engine_FDScript import blacklist_ops as bl


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args or not args[0].strip():
        await _send_error(ch, FDLogicError(
            "`$blackListServer` requires at least one server ID/name — "
            "example: `$blackListServer[serverID/servername; ...; Custom Error Message]`"
        ))
        return

    targets, custom_error = bl.parse_blacklist_args(args, ctx)
    if not targets:
        await _send_error(ch, FDLogicError("`$blackListServer` — target server cannot be empty."))
        return

    guild = ctx.interaction.guild if ctx.interaction else (ctx.message.guild if ctx.message else None)
    is_blocked, matched_info = bl.check_server_blocked(targets, guild)

    default_err = f"`$blackListServer` — This server `{matched_info}` is blacklisted from using this command."
    await bl.enforce_blacklist(
        cmd_name="blackListServer",
        is_blocked=is_blocked,
        matched_info=matched_info,
        custom_error=custom_error,
        ctx=ctx,
        default_err_text=default_err,
    )