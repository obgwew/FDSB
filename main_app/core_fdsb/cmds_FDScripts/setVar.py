# cmds_FDScripts/setVar.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error, _load_data, _save_data,
    _truncate,
)
from FDCore import _load_ids_data, _save_ids_data


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) == 2:
        name  = ctx.resolve(args[0]).strip()
        value = ctx.resolve(args[1])

        if not name:
            await _send_error(ch, FDLogicError("`$setVar` — variable name cannot be empty."))
            return

        data = _load_data()
        existed = name in data
        data[name] = value
        _save_data(data)

        if not existed:
            ctx.log_event(f"setVar [{name}] ← {_truncate(value)!r} (created — first time, global)")
            await _send_error(ch, FDEnvironmentError(
                f"Variable `{name}` did not exist and has been created with the "
                f"provided value. Script stopped — please review the program."
            ))
            return

        ctx.log_event(f"setVar [{name}] ← {_truncate(value)!r} (persistent)")

    elif len(args) == 3:
        name    = ctx.resolve(args[0]).strip()
        value   = ctx.resolve(args[1])
        user_id = ctx.resolve(args[2]).strip()

        if not name:
            await _send_error(ch, FDLogicError("`$setVar` — variable name cannot be empty."))
            return
        if not user_id:
            await _send_error(ch, FDLogicError("`$setVar` — user ID cannot be empty."))
            return

        global_data = _load_data()
        ids_data = _load_ids_data()

        if name not in ids_data:
            ids_data[name] = {}
        ids_data[name][user_id] = value
        _save_ids_data(ids_data)

        if name not in global_data:
            ctx.log_event(
                f"setVar [{name}] for user {user_id} ← {_truncate(value)!r} "
                f"(created — private, no matching global variable)"
            )
            await _send_error(ch, FDEnvironmentError(
                f"No global variable `{name}` exists. A private variable "
                f"`{name}` has been created for user `{user_id}` with the "
                f"provided value. Script stopped — please review the program."
            ))
            return

        ctx.log_event(f"setVar [{name}] for user {user_id} ← {_truncate(value)!r} (persistent)")

    else:
        await _send_error(ch, FDLogicError(
            "`$setVar` requires 2 or 3 arguments: `$setVar[name; value]` or `$setVar[name; value; user_id]`"
        ))