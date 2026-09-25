# cmds_FDScripts/resetUserVar.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError,
    _send_error,
)
from FDCore import _get_user_vars_dir, _delete_scoped_key


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) not in (1, 2, 3):
        await _send_error(ch, FDLogicError(
            "`$resetUserVar` requires 1 to 3 arguments: `$resetUserVar[name]`, "
            "`$resetUserVar[name; user_id]` or `$resetUserVar[name; user_id; guild_id]`"
        ))
        return

    name = ctx.resolve(args[0]).strip()
    if not name:
        await _send_error(ch, FDLogicError("`$resetUserVar` — variable name cannot be empty."))
        return

    user_id = ctx.resolve(args[1]).strip() if len(args) >= 2 else ctx.builtins.get("authorID", "")
    if not user_id:
        await _send_error(ch, FDLogicError("`$resetUserVar` — user ID cannot be empty."))
        return

    guild_id = ctx.resolve(args[2]).strip() if len(args) == 3 else ctx.builtins.get("guildID", "DM")
    if not guild_id:
        await _send_error(ch, FDLogicError("`$resetUserVar` — guild ID cannot be empty."))
        return

    removed = _delete_scoped_key(_get_user_vars_dir(), name, f"{guild_id}:{user_id}")
    ctx.log_event(
        f"resetUserVar [{name}] for user {user_id} in guild {guild_id} → "
        f"{'deleted' if removed else 'was already unset'}"
    )