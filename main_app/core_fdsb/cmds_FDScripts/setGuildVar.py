# cmds_FDScripts/setGuildVar.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error, _truncate,
    _load_data, _save_data,
)
from FDCore import _get_guild_vars_dir, _load_scoped_var, _save_scoped_var


def _apply(args: list[str], ctx: ExecutionContext):
    if len(args) not in (2, 3):
        return FDLogicError(
            "`$setGuildVar` requires 2 or 3 arguments: `$setGuildVar[name; value]` "
            "or `$setGuildVar[name; value; guild_id]`"
        )

    name  = ctx.resolve(args[0]).strip()
    value = ctx.resolve(args[1])
    if not name:
        return FDLogicError("`$setGuildVar` — variable name cannot be empty.")

    guild_id = ctx.resolve(args[2]).strip() if len(args) == 3 else ctx.builtins.get("guildID", "DM")
    if not guild_id:
        return FDLogicError("`$setGuildVar` — guild ID cannot be empty.")

    base_dir = _get_guild_vars_dir()
    values = _load_scoped_var(base_dir, name)
    existed = guild_id in values
    values[guild_id] = value
    _save_scoped_var(base_dir, name, values)

    global_data = _load_data()
    if name not in global_data:
        global_data[name] = ""
        _save_data(global_data)
        ctx.log_event(
            f"setGuildVar [{name}] for guild {guild_id} ← {_truncate(value)!r} "
            f"(created — no matching global variable)"
        )
        return FDEnvironmentError(
            f"No global variable `{name}` exists. A guild variable "
            f"`{name}` has been created for guild `{guild_id}` with the "
            f"provided value. Script stopped — please review the program."
        )

    ctx.log_event(
        f"setGuildVar [{name}] for guild {guild_id} "
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