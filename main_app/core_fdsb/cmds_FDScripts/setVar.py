# cmds_FDScripts/setVar.py
import discord
from main_app.core_fdsb.FDCore import (
    ExecutionContext, Command,
    FDLogicError, FDRuntimeError, FDEnvironmentError,
    _send_error, _load_data, _save_data,
    _load_ids_data, _save_ids_data, _truncate,
)


def _fmt(err) -> str:
    return f"{err._icon} **{err._category}** — {err.msg}"

async def _send_warning(ch, warning) -> None:
    ctx = getattr(ch, 'ctx', None)
    if ctx is not None and getattr(ctx, 'suppress_errors', False):
        ctx.log_event(f"[suppressed warning] {warning._category}: {warning.msg}")
        return
    if ch is not None:
        try:
            await ch.send(_fmt(warning))
        except Exception as e:
            print(f"[FDScript Warning Logger] Failed to send warning to channel: {e}")
    else:
        print(f"[FDScript Console Warning] {warning._category}: {warning.msg}")

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return _fmt(FDLogicError("`$setVar` cannot be used inline — use it as a standalone command."))

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) == 3:
        name    = ctx.resolve(args[0]).strip()
        value   = ctx.resolve(args[1])
        user_id = ctx.resolve(args[2]).strip()

        if not name:
            await _send_error(ch, FDLogicError("`$setVar` — variable name cannot be empty."))
            return
        if not user_id:
            await _send_error(ch, FDLogicError("`$setVar` — user ID cannot be empty."))
            return

        data = _load_ids_data()
        global_data = _load_data()
        
        existed = name in data and user_id in data.get(name, {})
        global_exists = name in global_data
        
        if name not in data:
            data[name] = {}
        data[name][user_id] = value
        _save_ids_data(data)
        ctx.log_event(f"setVar [{name}] for user {user_id} ← {_truncate(value)!r} (persistent)")

        if not existed and not global_exists:
            await _send_warning(ch, FDEnvironmentError(
                f"Variable `{name}` is not among the predefined variables. "
                f"A new variable `{name}` has been created with the provided value. "
                f"Please review the program if you would like to adjust this."
            ))

    elif len(args) == 2:
        name  = ctx.resolve(args[0]).strip()
        value = ctx.resolve(args[1])

        if not name:
            await _send_error(ch, FDLogicError("`$setVar` — variable name cannot be empty."))
            return

        data = _load_data()
        existed = name in data
        data[name] = value
        _save_data(data)
        ctx.log_event(f"setVar [{name}] ← {_truncate(value)!r} (persistent)")

        if not existed:
            await _send_warning(ch, FDEnvironmentError(
                f"Variable `{name}` is not among the predefined variables. "
                f"A new variable `{name}` has been created with the provided value. "
                f"Please review the program if you would like to adjust this."
            ))

    else:
        await _send_error(ch, FDLogicError(
            "`$setVar` requires 2 or 3 arguments: `$setVar[name; value]` or `$setVar[name; value; user_id]`"
        ))