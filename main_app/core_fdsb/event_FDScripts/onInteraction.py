# main_app/core_fdsb/event_FDScripts/onInteraction.py
import os
import asyncio
import discord

from main_app.core_fdsb.FDScript import run_script


async def handle_event(interaction: discord.Interaction, bot: discord.Client,
                        custom_id: str, events_dir: str) -> None:
    if not os.path.isdir(events_dir):
        return

    for fname in os.listdir(events_dir):
        fpath = os.path.join(events_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                script_text = f.read()

            if not script_text.strip():
                continue

            first_line = script_text.split('\n')[0].strip().replace(" ", "").lower()

            if not first_line.startswith("#prefix:$oninteraction"):
                continue

            if first_line == "#prefix:$oninteraction":
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
                continue

            try:
                button_id_in_file = first_line.split('[')[1].split(']')[0]

                if button_id_in_file == custom_id.lower():
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
            except IndexError:
                pass  

        except Exception as e:
            print(f"[Interaction Error] Failed to execute {fname}: {e}")