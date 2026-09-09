# main_app/core_bcfd/event_FDScripts/onJoined.py
import discord
import re
from main_app.core_fdsb.FDCore import ExecutionContext
from main_app.core_fdsb.FDScript import Interpreter

async def handle_event(member: discord.Member, bot: discord.Client, script_text: str):
    interpreter = Interpreter(script_text)
    ctx = ExecutionContext(message=None, bot=bot, member=member)
    
    first_line = script_text.split('\n')[0]
    match = re.search(r'\[(\d+)\]', first_line)
    if match:
        channel_id = int(match.group(1))
        target_channel = bot.get_channel(channel_id)
        if target_channel:
            ctx.message.channel = target_channel
        else:
            print(f"[Bot] ❌ الروم {channel_id} غير موجود أو البوت لا يملك صلاحية رؤيته لحدث onJoined")

    await interpreter.run(ctx)