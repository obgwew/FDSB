# main_app/core_fdsb/event_FDScripts/messageContainsAll.py
import discord

from main_app.core_fdsb.FDScript import run_script
from main_app.core_fdsb.event_FDScripts._event_scan import iter_event_files, extract_words

_PREFIX = "#prefix:$messagecontainsall"


async def handle_event(message: discord.Message, bot: discord.Client, events_dir: str) -> None:
    content_lower = message.content.lower()
    fgs_marked = False

    for fname, script_text, first_line in iter_event_files(events_dir):
        if not first_line.startswith(_PREFIX):
            continue

        words = extract_words(first_line)
        if not words:
            continue

        if not all(word in content_lower for word in words):
            continue

        if not fgs_marked:
            from main_app.core_fdsb.Server import set_fgs_state, STATE_SYNCING
            set_fgs_state(STATE_SYNCING)
            fgs_marked = True

        try:
            await run_script(message, bot, script_text)
        except Exception as e:
            print(f"[messageContainsAll Error] Failed to execute {fname}: {e}")