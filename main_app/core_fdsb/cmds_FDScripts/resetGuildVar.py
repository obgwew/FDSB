# cmds_FDScripts/resetGuildVar.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError,
    _send_error,
)
from FDCore import _get_guild_vars_dir, _delete_scoped_key


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) not in (1, 2):
        await _send_error(ch, FDLogicError(
            "`$resetGuildVar` requires 1 or 2 arguments: `$resetGuildVar[name]` "
            "or `$resetGuildVar[name; guild_id]`"
        ))
        return

    name = ctx.resolve(args[0]).strip()
    if not name:
        await _send_error(ch, FDLogicError("`$resetGuildVar` — variable name cannot be empty."))
        return

    guild_id = ctx.resolve(args[1]).strip() if len(args) == 2 else ctx.builtins.get("guildID", "DM")
    if not guild_id:
        await _send_error(ch, FDLogicError("`$resetGuildVar` — guild ID cannot be empty."))
        return

    removed = _delete_scoped_key(_get_guild_vars_dir(), name, guild_id)
    ctx.log_event(
        f"resetGuildVar [{name}] for guild {guild_id} → "
        f"{'deleted' if removed else 'was already unset'}"
    )