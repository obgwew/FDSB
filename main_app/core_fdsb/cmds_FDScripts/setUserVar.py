# cmds_FDScripts/setUserVar.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error, _truncate,
    _load_data, _save_data,
)
from FDCore import _get_user_vars_dir, _load_scoped_var, _save_scoped_var


def _apply(args: list[str], ctx: ExecutionContext):
    if len(args) not in (2, 3, 4):
        return FDLogicError(
            "`$setUserVar` requires 2 to 4 arguments: `$setUserVar[name; value]`, "
            "`$setUserVar[name; value; user_id]` or `$setUserVar[name; value; user_id; guild_id]`"
        )

    name  = ctx.resolve(args[0]).strip()
    value = ctx.resolve(args[1])
    if not name:
        return FDLogicError("`$setUserVar` — variable name cannot be empty.")

    user_id = ctx.resolve(args[2]).strip() if len(args) >= 3 else ctx.builtins.get("authorID", "")
    if not user_id:
        return FDLogicError("`$setUserVar` — user ID cannot be empty.")

    guild_id = ctx.resolve(args[3]).strip() if len(args) == 4 else ctx.builtins.get("guildID", "DM")
    if not guild_id:
        return FDLogicError("`$setUserVar` — guild ID cannot be empty.")

    key = f"{guild_id}:{user_id}"
    base_dir = _get_user_vars_dir()
    values = _load_scoped_var(base_dir, name)
    existed = key in values
    values[key] = value
    _save_scoped_var(base_dir, name, values)

    global_data = _load_data()
    if name not in global_data:
        global_data[name] = ""
        _save_data(global_data)
        ctx.log_event(
            f"setUserVar [{name}] for user {user_id} in guild {guild_id} ← {_truncate(value)!r} "
            f"(created — private, no matching global variable)"
        )
        return FDEnvironmentError(
            f"No global variable `{name}` exists. A user variable `{name}` has been "
            f"created for user `{user_id}` in guild `{guild_id}` with the provided value. "
            f"Script stopped — please review the program."
        )

    ctx.log_event(
        f"setUserVar [{name}] for user {user_id} in guild {guild_id} "
        f"← {_truncate(value)!r} ({'updated' if existed else 'created'})"
    )
    return None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    err = _apply(args, ctx)
    if err is not None:
        ctx._abort_with_error(err)
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    err = _apply(args, ctx)
    if err is not None:
        await _send_error(ch, err)