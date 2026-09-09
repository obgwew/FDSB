# main_app/core_fdsb/event_FDScripts/onBoostServer.py
import discord
from main_app.core_fdsb.FDScript import run_script

async def handle_event(message: discord.Message, bot: discord.Client, script_text: str):

    try:
        await run_script(message, bot, script_text, is_event=True)
    except Exception as e:
        print(f"[onBoostServer Event Error] : {e}")