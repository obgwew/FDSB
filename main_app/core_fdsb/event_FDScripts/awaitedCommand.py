# main_app/core_fdsb/event_FDScripts/awaitedCommand.py
import os
import re

_PREFIX = "#prefix:$awaitedcommand["

_waits: dict[tuple[int, int | None], str] = {}


def register_wait(channel_id: int, user_id: int | None, name: str) -> None:
    _waits[(channel_id, user_id)] = name.lower()


def scan_scripts(events_dir: str, prefix: str, name: str) -> list[tuple[str, str]]:
    try:
        files = os.listdir(events_dir)
    except OSError:
        return []

    found = []
    for fname in files:
        path = os.path.join(events_dir, fname)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue

        lines = text.splitlines()
        first = lines[0].strip() if lines else ""
        if not first.lower().replace(" ", "").startswith(prefix):
            continue

        start, end = first.find("["), first.rfind("]")
        if start == -1 or end <= start:
            continue
        parts = [p.strip() for p in first[start + 1:end].split(";")]
        if parts[0].lower() != name:
            continue

        try:
            ctime = os.path.getctime(path)
        except OSError:
            ctime = 0
        found.append((ctime, text, parts[1] if len(parts) > 1 else ""))

    found.sort(key=lambda item: item[0])
    return [(text, flt) for _, text, flt in found]


def _passes(flt: str, content: str) -> bool:
    if not flt:
        return True
    if not (flt.startswith("<") and flt.endswith(">")):
        return False
    rule = flt[1:-1].strip()
    if rule.lower() == "numeric":
        return re.fullmatch(r"-?\d+(\.\d+)?", content) is not None
    options = [o.strip().lower() for o in rule.split("/") if o.strip()]
    return content.lower() in options


async def handle_event(message, bot, events_dir: str) -> bool:
    channel_id = message.channel.id
    name = _waits.pop((channel_id, message.author.id), None)
    if name is None:
        name = _waits.pop((channel_id, None), None)
    if name is None:
        return False

    from main_app.core_fdsb.FDScript import run_script

    content = message.content.strip()
    callbacks = scan_scripts(events_dir, _PREFIX, name)
    scripts = [text for text, flt in callbacks if _passes(flt, content)]

    if callbacks and not scripts:
        from main_app.core_fdsb.event_FDScripts.awaitedCommandError import (
            handle_event as handle_error,
        )
        return await handle_error(message, bot, events_dir, name)

    ran = False
    for script_text in scripts:
        try:
            await run_script(message, bot, script_text, is_event=True)
            ran = True
        except Exception as e:
            print(f"[awaitedCommand Event Error] : {e}")
    return ran