# cmds_FDScripts/getVar.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDEnvironmentError,
    _send_error, _load_data, _save_data,
    _truncate,
)
from FDCore import _load_ids_data, _save_ids_data


def _display(value) -> str:
    return "" if value is None else str(value)


def _fetch_global(name: str) -> tuple[object, bool]:
    data = _load_data()
    if name in data:
        return data[name], False
    data[name] = None
    _save_data(data)
    return None, True


def _fetch_scoped(name: str, user_id: str) -> tuple[object, bool]:
    global_data = _load_data()
    ids_data = _load_ids_data()

    if name in global_data:
        user_val = ids_data.get(name, {}).get(user_id)
        if user_val is not None:
            return user_val, False
        return global_data[name], False

    if name not in ids_data:
        ids_data[name] = {}
    ids_data[name][user_id] = None
    _save_ids_data(ids_data)
    return None, True


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    resolved = [ctx.resolve(a) for a in args]

    if len(resolved) == 1:
        name = resolved[0].strip()
        if not name:
            return ""
        value, is_new = _fetch_global(name)
        if is_new:
            ctx._abort_with_error(FDEnvironmentError(
                f"Variable `{name}` did not exist and has been created for the "
                f"first time (value: none). Script stopped — please review."
            ))
            return ""
        ctx.log_event(f"getVar [{name}] → {_truncate(_display(value))!r}")
        return _display(value)

    if len(resolved) == 2:
        name, user_id = resolved[0].strip(), resolved[1].strip()
        if not name or not user_id:
            return ""
        value, must_stop = _fetch_scoped(name, user_id)
        if must_stop:
            ctx._abort_with_error(FDEnvironmentError(
                f"No global variable `{name}` exists. A private variable "
                f"`{name}` has been created for user `{user_id}` (value: none). "
                f"Script stopped."
            ))
            return ""
        ctx.log_event(f"getVar [{name}] for user {user_id} → {_truncate(_display(value))!r}")
        return _display(value)

    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved = [ctx.resolve(a) for a in args]

    if len(resolved) == 1:
        name = resolved[0].strip()
        if not name:
            await _send_error(ch, FDEnvironmentError("`$getVar` — variable name cannot be empty."))
            return

        value, is_new = _fetch_global(name)
        if is_new:
            await _send_error(ch, FDEnvironmentError(
                f"Variable `{name}` did not exist and has been created for the "
                f"first time (value: none). Please review the program."
            ))
            return

        ctx.log_event(f"getVar [{name}] → {_truncate(_display(value))!r}")
        if value is not None:
            await ch.send(_display(value))

    elif len(resolved) == 2:
        name, user_id = resolved[0].strip(), resolved[1].strip()
        if not name:
            await _send_error(ch, FDEnvironmentError("`$getVar` — variable name cannot be empty."))
            return
        if not user_id:
            await _send_error(ch, FDEnvironmentError("`$getVar` — user ID cannot be empty."))
            return

        value, must_stop = _fetch_scoped(name, user_id)
        if must_stop:
            await _send_error(ch, FDEnvironmentError(
                f"No global variable `{name}` exists. A private variable "
                f"`{name}` has been created for user `{user_id}` (value: none)."
            ))
            return

        ctx.log_event(f"getVar [{name}] for user {user_id} → {_truncate(_display(value))!r}")
        if value is not None:
            await ch.send(_display(value))

    else:
        await _send_error(ch, FDEnvironmentError(
            "`$getVar` requires 1 or 2 arguments: `$getVar[name]` or `$getVar[name; user_id]`"
        ))