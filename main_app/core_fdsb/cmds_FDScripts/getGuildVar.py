# cmds_FDScripts/getGuildVar.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error, _truncate,
    _load_data, _save_data,
)
from FDCore import _get_guild_vars_dir, _load_scoped_var, _save_scoped_var


def _fetch_guild_var(name: str, guild_id: str) -> tuple[object, bool]:
    global_data = _load_data()
    base_dir = _get_guild_vars_dir()
    values = _load_scoped_var(base_dir, name)

    if name in global_data:
        if guild_id in values and values[guild_id] is not None and values[guild_id] != "":
            return values[guild_id], False
        default_val = global_data[name]
        return ("" if default_val is None else str(default_val)), False

    global_data[name] = None
    _save_data(global_data)
    if guild_id not in values:
        values[guild_id] = None
        _save_scoped_var(base_dir, name, values)
    return None, True


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    resolved = [ctx.resolve(a) for a in args]
    if len(resolved) == 1:
        name, guild_id = resolved[0].strip(), ctx.builtins.get("guildID", "DM")
    elif len(resolved) == 2:
        name, guild_id = resolved[0].strip(), resolved[1].strip()
    else:
        return ""

    if not name or not guild_id:
        return ""

    val, must_stop = _fetch_guild_var(name, guild_id)
    if must_stop:
        ctx._abort_with_error(FDEnvironmentError(
            f"No global variable `{name}` exists. A guild variable `{name}` has been "
            f"created for guild `{guild_id}` (value: none). Script stopped."
        ))
        return ""

    display_val = "" if val is None else str(val)
    ctx.log_event(f"getGuildVar [{name}] for guild {guild_id} → {_truncate(display_val)!r}")
    return display_val


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved = [ctx.resolve(a) for a in args]
    if len(resolved) == 1:
        name, guild_id = resolved[0].strip(), ctx.builtins.get("guildID", "DM")
    elif len(resolved) == 2:
        name, guild_id = resolved[0].strip(), resolved[1].strip()
    else:
        await _send_error(ch, FDLogicError(
            "`$getGuildVar` requires 1 or 2 arguments: `$getGuildVar[name]` "
            "or `$getGuildVar[name; guild_id]`"
        ))
        return

    if not name:
        await _send_error(ch, FDLogicError("`$getGuildVar` — variable name cannot be empty."))
        return
    if not guild_id:
        await _send_error(ch, FDLogicError("`$getGuildVar` — guild ID cannot be empty."))
        return

    val, must_stop = _fetch_guild_var(name, guild_id)
    if must_stop:
        await _send_error(ch, FDEnvironmentError(
            f"No global variable `{name}` exists. A guild variable `{name}` has been "
            f"created for guild `{guild_id}` (value: none)."
        ))
        return

    display_val = "" if val is None else str(val)
    ctx.log_event(f"getGuildVar [{name}] for guild {guild_id} → {_truncate(display_val)!r}")
    if val is not None:
        await ch.send(display_val)