# main_app/core_fdsb/event_FDScripts/messageContains.py

import os
import discord

from main_app.core_fdsb.FDScript import run_script


def _extract_words(first_line_norm: str) -> list[str]:
    try:
        inside = first_line_norm.split('[', 1)[1].rsplit(']', 1)[0]
        return [w.strip() for w in inside.split(';') if w.strip()]
    except IndexError:
        return []


async def handle_event(message: discord.Message, bot: discord.Client, events_dir: str) -> None:
    if not os.path.isdir(events_dir):
        return

    content_lower = message.content.lower()

    for fname in os.listdir(events_dir):
        fpath = os.path.join(events_dir, fname)
        if not os.path.isfile(fpath):
            continue

        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                script_text = f.read()

            if not script_text.strip():
                continue

            first_line = script_text.split('\n')[0].strip()
            first_line_norm = first_line.replace(" ", "").lower()

            if not first_line_norm.startswith("#prefix:$messagecontains["):
                continue

            words = _extract_words(first_line_norm)
            if not words:
                continue

            if any(word in content_lower for word in words):
                await run_script(message, bot, script_text)

        except Exception as e:
            print(f"[messageContains Error] Failed to execute {fname}: {e}")