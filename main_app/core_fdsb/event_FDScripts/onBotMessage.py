# main_app/core_fdsb/event_FDScripts/onBotMessage.py
import os
import discord

from main_app.core_fdsb.FDScript import run_script


def _extract_self_arg(first_line_norm: str) -> str:
    try:
        inside = first_line_norm.split('[', 1)[1].rsplit(']', 1)[0]
        return inside.strip()
    except IndexError:
        return "no"


async def handle_event(message: discord.Message, bot: discord.Client, events_dir: str) -> None:
    if not os.path.isdir(events_dir):
        return

    if not message.author.bot:
        return

    is_self = bot.user is not None and message.author.id == bot.user.id

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

            if not first_line_norm.startswith("#prefix:$onbotmessage["):
                continue

            self_arg = _extract_self_arg(first_line_norm)
            follow_self = self_arg == "yes"

            if is_self and not follow_self:
                continue

            await run_script(message, bot, script_text, is_event=True)

        except Exception as e:
            print(f"[onBotMessage Error] Failed to execute {fname}: {e}")