# cmds_FDScripts/setBotStatus.py
import time
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError, FDRuntimeError,
    _send_error,
)

_STATUS_MAP: dict[str, discord.Status] = {
    "online":     discord.Status.online,
    "idle":       discord.Status.idle,
    "dnd":        discord.Status.dnd,
    "invisible":  discord.Status.invisible,
    "offline":    discord.Status.invisible,
}

_COOLDOWN_SECONDS = 12
_last_used: float = 0.0


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    global _last_used

    if not args or not args[0].strip():
        await _send_error(ch, FDLogicError(
            "`$setBotStatus` requires 1 argument: "
            "`$setBotStatus[online | idle | dnd | invisible]`"
        ))
        return

    now = time.time()
    remaining = _COOLDOWN_SECONDS - (now - _last_used)
    if remaining > 0:
        wait = int(remaining) + (1 if remaining % 1 else 0) 
        await _send_error(ch, FDEnvironmentError(
            f"`$setBotStatus` — please wait **{wait}s** before using this command again."
        ))
        return

    raw = ctx.resolve(args[0]).strip().lower().replace(" ", "_").replace("-", "_")

    status = _STATUS_MAP.get(raw)
    if status is None:
        await _send_error(ch, FDLogicError(
            f"`$setBotStatus` — unknown status `{raw}`.\n"
            f"Valid values: `online`, `idle`, `dnd`, `invisible`"
        ))
        return

    bot = ctx.bot
    if bot is None or bot.user is None:
        await _send_error(ch, FDEnvironmentError(
            "`$setBotStatus` — bot is not ready"
        ))
        return

    try:
        activity = bot.activity
        await bot.change_presence(status=status, activity=activity)
    except discord.HTTPException as e:
        await _send_error(ch, FDRuntimeError(
            f"`$setBotStatus` — failed to change presence: `{e}`"
        ))
        return
    except Exception as e:
        await _send_error(ch, FDRuntimeError(
            f"`$setBotStatus` — unexpected error: `{e}`"
        ))
        return

    _last_used = now

    try:
        _persist_status(bot, raw if raw != "offline" else "invisible")
    except Exception:
        pass

    ctx.log_event(f"setBotStatus → {raw}")


def _persist_status(bot: discord.Client, status_key: str) -> None:
    import os
    import json

    candidates = []
    for attr in ("bot_dir", "data_dir", "root_dir"):
        d = getattr(bot, attr, None)
        if d:
            candidates.append(os.path.join(os.path.abspath(d), "bot_files", "status_config.json"))
            candidates.append(os.path.join(os.path.abspath(d), "status_config.json"))

    cwd = os.getcwd()
    candidates.append(os.path.join(cwd, "bot_files", "status_config.json"))
    candidates.append(os.path.join(cwd, "status_config.json"))

    path = next((p for p in candidates if os.path.isfile(p)), None)
    if not path:
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data["status"] = status_key

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
