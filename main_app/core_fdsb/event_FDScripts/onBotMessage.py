# main_app/core_fdsb/event_FDScripts/onBotMessage.py
import discord

from main_app.core_fdsb.FDScript import run_script
from main_app.core_fdsb.event_FDScripts._event_scan import iter_event_files, extract_bracket_content

_PREFIX = "#prefix:$onbotmessage["


async def handle_event(message: discord.Message, bot: discord.Client, events_dir: str) -> None:
    if not message.author.bot:
        return

    is_self = bot.user is not None and message.author.id == bot.user.id

    for fname, script_text, first_line in iter_event_files(events_dir):
        if not first_line.startswith(_PREFIX):
            continue

        self_arg = extract_bracket_content(first_line) or "no"
        follow_self = self_arg == "yes"

        if is_self and not follow_self:
            continue

        try:
            await run_script(message, bot, script_text, is_event=True)
        except Exception as e:
            print(f"[onBotMessage Error] Failed to execute {fname}: {e}")