# cmds_FDScripts/getUserVar.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error, _truncate,
    _load_data, _save_data,
)
from FDCore import _get_user_vars_dir, _load_scoped_var, _save_scoped_var


def _resolve_args(resolved: list[str], ctx: ExecutionContext) -> 'tuple[str, str, str] | None':
    if len(resolved) == 1:
        name = resolved[0].strip()
        user_id = ctx.builtins.get("authorID", "")
        guild_id = ctx.builtins.get("guildID", "DM")
    elif len(resolved) == 2:
        name = resolved[0].strip()
        user_id = resolved[1].strip()
        guild_id = ctx.builtins.get("guildID", "DM")
    elif len(resolved) == 3:
        name = resolved[0].strip()
        user_id = resolved[1].strip()
        guild_id = resolved[2].strip()
    else:
        return None
    return name, user_id, guild_id


def _fetch_user_var(name: str, guild_id: str, user_id: str) -> tuple[object, bool]:
    global_data = _load_data()
    base_dir = _get_user_vars_dir()
    values = _load_scoped_var(base_dir, name)
    key = f"{guild_id}:{user_id}"

    if name in global_data:
        user_val = values.get(key)
        if user_val is not None and user_val != "":
            return user_val, False
        default_val = global_data[name]
        return ("" if default_val is None else str(default_val)), False

    global_data[name] = None
    _save_data(global_data)
    if key not in values:
        values[key] = None
        _save_scoped_var(base_dir, name, values)
    return None, True


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    resolved = [ctx.resolve(a) for a in args]
    parsed = _resolve_args(resolved, ctx)
    if parsed is None:
        return ""

    name, user_id, guild_id = parsed
    if not name or not user_id or not guild_id:
        return ""

    val, must_stop = _fetch_user_var(name, guild_id, user_id)
    if must_stop:
        ctx._abort_with_error(FDEnvironmentError(
            f"No global variable `{name}` exists. A user variable `{name}` has been "
            f"created for user `{user_id}` (value: none). Script stopped."
        ))
        return ""

    display_val = "" if val is None else str(val)
    ctx.log_event(f"getUserVar [{name}] for user {user_id} in guild {guild_id} → {_truncate(display_val)!r}")
    return display_val


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved = [ctx.resolve(a) for a in args]
    parsed = _resolve_args(resolved, ctx)
    if parsed is None:
        await _send_error(ch, FDLogicError(
            "`$getUserVar` requires 1 to 3 arguments: `$getUserVar[name]`, "
            "`$getUserVar[name; user_id]` or `$getUserVar[name; user_id; guild_id]`"
        ))
        return

    name, user_id, guild_id = parsed
    if not name:
        await _send_error(ch, FDLogicError("`$getUserVar` — variable name cannot be empty."))
        return
    if not user_id:
        await _send_error(ch, FDLogicError("`$getUserVar` — user ID cannot be empty."))
        return
    if not guild_id:
        await _send_error(ch, FDLogicError("`$getUserVar` — guild ID cannot be empty."))
        return

    val, must_stop = _fetch_user_var(name, guild_id, user_id)
    if must_stop:
        await _send_error(ch, FDEnvironmentError(
            f"No global variable `{name}` exists. A user variable `{name}` has been "
            f"created for user `{user_id}` (value: none)."
        ))
        return

    display_val = "" if val is None else str(val)
    ctx.log_event(f"getUserVar [{name}] for user {user_id} in guild {guild_id} → {_truncate(display_val)!r}")
    if val is not None:
        await ch.send(display_val)