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


class _DummyChannel:
    id = 0
    name = "unknown"


class _BanEventMessage:

    def __init__(self, user: discord.User | discord.Member, guild: discord.Guild, channel: discord.abc.Messageable | None = None):
        self.channel = channel or _DummyChannel()
        self.guild = guild
        self.author = user
        self.content = ""
        self.id = 0


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


def build_ban_context(bot: discord.Client, guild: discord.Guild,
                      user: discord.User | discord.Member,
                      script_text: str, event_label: str) -> ExecutionContext:
    first_line = script_text.split('\n')[0]
    match = _CHANNEL_ID_RE.search(first_line)
    target_channel = None

    if match:
        channel_id = int(match.group(1))
        target_channel = bot.get_channel(channel_id)
        if not target_channel:
            print(f"[Bot] Channel {channel_id} not found or bot lacks permission for {event_label} event")

    fake_message = _BanEventMessage(user, guild, target_channel)
    ctx = ExecutionContext(
        message=fake_message,
        bot=bot,
        member=user if isinstance(user, discord.Member) else None,
        is_event=True
    )

    ctx.builtins["authorID"] = str(user.id)
    ctx.builtins["authorName"] = user.name
    ctx.builtins["mention"] = user.mention
    ctx.builtins["guildID"] = str(guild.id)
    ctx.builtins["guildName"] = guild.name
    if target_channel:
        ctx.builtins["channelID"] = str(target_channel.id)
        ctx.builtins["channelName"] = getattr(target_channel, "name", "")

    return ctx