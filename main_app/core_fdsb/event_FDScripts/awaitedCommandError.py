# main_app/core_fdsb/event_FDScripts/awaitedCommandError.py
from main_app.core_fdsb.event_FDScripts.awaitedCommand import scan_scripts

_PREFIX = "#prefix:$awaitedcommanderror["


async def handle_event(message, bot, events_dir: str, name: str) -> bool:
    from main_app.core_fdsb.FDScript import run_script

    ran = False
    for script_text, _ in scan_scripts(events_dir, _PREFIX, name.lower()):
        try:
            await run_script(message, bot, script_text, is_event=True)
            ran = True
        except Exception as e:
            print(f"[awaitedCommandError Event Error] : {e}")
    return ran