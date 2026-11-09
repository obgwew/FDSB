# main_app/core_fdsb/event_FDScripts/task.py
import asyncio
import os
import re

_PREFIX         = "#prefix:$task["
_TIME_RE        = re.compile(r"(\d+)([smhd])")
_UNITS          = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_RESCAN_SECONDS = 10

_supervisor: "asyncio.Task | None" = None
_bot = None
_state: dict = {}


class _TaskMessage:
    id = 0
    content = ""
    channel = None
    guild = None

    def __init__(self, bot):
        self.author = bot.user


def _read_task(path: str, fname: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return None

    lines = text.splitlines()
    first = lines[0].strip() if lines else ""
    if not first.lower().replace(" ", "").startswith(_PREFIX):
        return None

    start, end = first.find("["), first.rfind("]")
    match = None
    if start != -1 and end > start:
        match = _TIME_RE.fullmatch(first[start + 1:end].replace(" ", "").lower())
    if match is None or int(match.group(1)) < 1:
        print(f"[task Event Error] : {fname}: invalid time, use a whole number followed by "
              f"s, m, h or d (e.g. 30s, 5m, 2h, 1d)")
        return None
    return text, int(match.group(1)) * _UNITS[match.group(2)]


async def _run_once(bot, script_text: str) -> None:
    from main_app.core_fdsb.FDScript import Interpreter, ExecutionContext

    ctx = ExecutionContext(None, bot, is_event=True)
    ctx.message = _TaskMessage(bot)
    ctx.builtins = {
        "botID":   str(bot.user.id) if bot.user else "",
        "botName": bot.user.name if bot.user else "",
    }
    await Interpreter(script_text).run(ctx)


async def _run_task(bot, fname: str, script_text: str, interval: int) -> None:
    loop = asyncio.get_running_loop()
    next_run = loop.time() + interval
    while True:
        await asyncio.sleep(max(0.0, next_run - loop.time()))
        try:
            await _run_once(bot, script_text)
        except Exception as e:
            print(f"[task Event Error] : {fname}: {e}")
        next_run += interval
        now = loop.time()
        if next_run <= now:
            next_run += interval * (int((now - next_run) // interval) + 1)


def _reconcile(bot, events_dir: str) -> None:
    try:
        files = os.listdir(events_dir)
    except OSError:
        files = []

    new_state: dict = {}
    for fname in files:
        path = os.path.join(events_dir, fname)
        try:
            st = os.stat(path)
        except OSError:
            continue
        if not os.path.isfile(path):
            continue

        sig = (st.st_mtime_ns, st.st_size)
        prev = _state.get(fname)
        if prev is not None and prev[0] == sig:
            new_state[fname] = prev
            continue
        if prev is not None and prev[1] is not None:
            prev[1].cancel()

        parsed = _read_task(path, fname)
        task = None
        if parsed is not None:
            task = asyncio.create_task(_run_task(bot, fname, parsed[0], parsed[1]))
        new_state[fname] = (sig, task)

    for fname, (_, task) in _state.items():
        if fname not in new_state and task is not None:
            task.cancel()
    _state.clear()
    _state.update(new_state)


async def _supervise(bot, events_dir: str) -> None:
    while True:
        try:
            _reconcile(bot, events_dir)
        except Exception as e:
            print(f"[task Event Error] : {e}")
        await asyncio.sleep(_RESCAN_SECONDS)


def _stop_all() -> None:
    global _supervisor
    for _, task in _state.values():
        if task is not None:
            try:
                task.cancel()
            except Exception:
                pass
    _state.clear()
    if _supervisor is not None:
        try:
            _supervisor.cancel()
        except Exception:
            pass
        _supervisor = None


async def handle_event(bot, events_dir: str) -> None:
    global _supervisor, _bot
    if _supervisor is not None and not _supervisor.done() and _bot is bot:
        return
    _stop_all()
    _bot = bot
    _supervisor = asyncio.create_task(_supervise(bot, events_dir))