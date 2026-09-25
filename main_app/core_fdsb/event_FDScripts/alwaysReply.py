# main_app/core_fdsb/event_FDScripts/alwaysReply.py
import discord
from main_app.core_fdsb.FDScript import run_script

async def handle_event(message: discord.Message, bot: discord.Client, script_text: str):
    from main_app.core_fdsb.Server import set_fgs_state, STATE_SYNCING
    set_fgs_state(STATE_SYNCING)
    await run_script(message, bot, script_text, is_event=True, is_reply=True)
