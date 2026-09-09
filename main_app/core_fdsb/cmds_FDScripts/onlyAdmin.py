# cmds_FDScripts/onlyAdmin.py
import discord
from FDScript import ExecutionContext, Command, FDEnvironmentError, FDAbortScript, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not ctx.message.guild:
        return "false"
    author = ctx.message.author
    is_owner = (author.id == ctx.message.guild.owner_id)
    is_admin = getattr(author.guild_permissions, 'administrator', False)
    return "true" if (is_owner or is_admin) else "false"


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not ctx.message.guild:
        await _send_error(ch, FDEnvironmentError("`$onlyAdmin` can only be used within a server."))
        return

    author = ctx.message.author
    is_owner = (author.id == ctx.message.guild.owner_id)
    is_admin = getattr(author.guild_permissions, 'administrator', False)

    if not (is_owner or is_admin):
        error_msg = "".join(ctx.resolve(arg) for arg in args).strip()

        ctx.stop_typing()
        if error_msg:
            dest = await ctx.get_dest()
            sent = await dest.send(error_msg)
            ctx.last_bot_message = sent

        ctx.log_event("onlyAdmin → Failed. Aborting script execution.")
        raise FDAbortScript()

    ctx.log_event("onlyAdmin → Passed.")