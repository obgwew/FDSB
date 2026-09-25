# main_app/core_fdsb/event_FDScripts/_event_context.py

import re
import discord

from main_app.core_fdsb.FDCore import ExecutionContext

_CHANNEL_ID_RE = re.compile(r'\[(\d+)\]')


class _EventMessage:

    def __init__(self, bot: discord.Client, member: discord.Member):
        self.channel = None
        self.guild = getattr(member, "guild", None)
        self.author = member
        self.content = ""


def build_member_context(bot: discord.Client, member: discord.Member,
                         script_text: str, event_label: str) -> ExecutionContext:
    fake_message = _EventMessage(bot, member)
    ctx = ExecutionContext(message=fake_message, bot=bot, member=member)

    first_line = script_text.split('\n')[0]
    match = _CHANNEL_ID_RE.search(first_line)
    if match:
        channel_id = int(match.group(1))
        target_channel = bot.get_channel(channel_id)
        if target_channel:
            ctx.message.channel = target_channel
        else:
            print(f"[Bot] Channel {channel_id} not found or bot lacks "
                  f"permission to view it for {event_label} event")

    return ctx