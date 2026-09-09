# cmds_FDScripts/getVar.py
import discord
from main_app.core_fdsb.FDCore import (
    ExecutionContext, Command,
    FDLogicError, FDRuntimeError, FDEnvironmentError,
    _send_error, _load_data, _save_data, _load_ids_data, _save_ids_data,
    _truncate,
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

def _ensure_exists(name: str, data: dict, save_fn, is_user_scoped: bool = False, user_id: str = None) -> bool:
    if is_user_scoped:
        global_data = _load_data()
        global_exists = name in global_data
        
        existed = name in data and user_id in data.get(name, {})
        if not existed:
            if name not in data:
                data[name] = {}
            data[name][user_id] = ''
            save_fn(data)
        
        return not existed and not global_exists
    else:
        existed = name in data
        if not existed:
            data[name] = ''
            save_fn(data)
        return not existed

def _get_value(args: list[str], ctx: ExecutionContext) -> tuple[str, bool, str]:
    resolved_args = [ctx.resolve(a) for a in args]

    if len(resolved_args) == 2:
        name    = resolved_args[0].strip()
        user_id = resolved_args[1].strip()
        if not name:
            ctx.log_event("getVar inline error: empty variable name")
            return "", False, name
        if not user_id:
            ctx.log_event("getVar inline error: empty user ID")
            return "", False, name

        data = _load_ids_data()
        warned = _ensure_exists(name, data, _save_ids_data, is_user_scoped=True, user_id=user_id)
        if warned:
            ctx.log_event(f"getVar warning: '{name}' is not a predefined variable — created with empty value")

        val = data.get(name, {}).get(user_id, '')
        ctx.log_event(f"getVar [{name}] for user {user_id} → {_truncate(val)!r}")
        return str(val), warned, name

    elif len(resolved_args) == 1:
        name = resolved_args[0].strip()
        if not name:
            ctx.log_event("getVar inline error: empty variable name")
            return "", False, name

        data = _load_data()
        warned = _ensure_exists(name, data, _save_data)
        if warned:
            ctx.log_event(f"getVar warning: '{name}' is not a predefined variable — created with empty value")

        val = str(data.get(name, ''))
        ctx.log_event(f"getVar [{name}] → {_truncate(val)!r}")
        return val, warned, name

    else:
        ctx.log_event("getVar inline error: invalid argument count")
        return "", False, ""

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    value, _warned, _name = _get_value(args, ctx)
    return value

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    value, warned, name = _get_value(args, ctx)

    if warned:
        await _send_warning(ch, FDEnvironmentError(
            f"Variable `{name}` is not among the predefined variables. "
            f"A new variable `{name}` has been created with an empty value. "
            f"Please review the program if you would like to adjust this."
        ))

    if value:
        await ch.send(value)