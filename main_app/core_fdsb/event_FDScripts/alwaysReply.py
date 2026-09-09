# main_app/core_fdsb/event_FDScripts/alwaysReply.py
import discord
from main_app.core_fdsb.FDScript import run_script

async def handle_event(message: discord.Message, bot: discord.Client, script_text: str):
    try:
        await run_script(message, bot, script_text, is_event=True, is_reply=True)
    except Exception as e:
        print(f"[alwaysReply Event Error] خطأ أثناء تنفيذ حدث الرد الدائم: {e}")