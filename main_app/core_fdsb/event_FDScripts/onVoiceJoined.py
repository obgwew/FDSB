# main_app/core_fdsb/event_FDScripts/onVoiceJoined.py
import discord
import re
from main_app.core_fdsb.FDCore import ExecutionContext
from main_app.core_fdsb.FDScript import Interpreter


async def handle_event(member: discord.Member, voice_channel: discord.VoiceChannel,
                        bot: discord.Client, script_text: str):
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
            print(f"[Bot] Channel {channel_id} not found or bot lacks permission to view it for $onVoiceJoined event")

    await interpreter.run(ctx)