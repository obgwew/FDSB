# main_app/core_fdsb/event_FDScripts/onInteraction.py
import asyncio
import discord

from main_app.core_fdsb.FDScript import run_script
from main_app.core_fdsb.event_FDScripts._event_scan import iter_event_files, extract_bracket_content

_PREFIX = "#prefix:$oninteraction"


def _schedule(interaction: discord.Interaction, bot: discord.Client, script_text: str) -> None:
    asyncio.create_task(
        run_script(
            message=interaction.message,
            bot=bot,
            script_text=script_text,
            is_event=True,
            is_reply=False,
            interaction=interaction,
        )
    )


async def handle_event(interaction: discord.Interaction, bot: discord.Client,
                        custom_id: str, events_dir: str) -> None:
    from main_app.core_fdsb.Server import set_fgs_state, STATE_SYNCING
    set_fgs_state(STATE_SYNCING)

    for fname, script_text, first_line in iter_event_files(events_dir):
        if not first_line.startswith(_PREFIX):
            continue

        try:
            if first_line == _PREFIX:
                _schedule(interaction, bot, script_text)
                continue

            button_id = extract_bracket_content(first_line)
            if button_id and button_id == custom_id.lower():
                _schedule(interaction, bot, script_text)
        except Exception as e:
            print(f"[Interaction Error] Failed to execute {fname}: {e}")