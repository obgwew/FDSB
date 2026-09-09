# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/event_FDScripts/onBotOnline.py
import discord
from main_app.core_fdsb.FDScript import run_script


class _FakeOnlineMessage:
    def __init__(self, channel: discord.abc.Messageable, bot: discord.Client):
        self.channel = channel
        self.guild = getattr(channel, "guild", None)
        self.author = bot.user
        self.content = ""


async def handle_event(bot: discord.Client, script_text: str, channel_id: str | None = None) -> None:
    ctx_source = None

    if channel_id:
        try:
            channel = bot.get_channel(int(channel_id))
            if channel is None:
                channel = await bot.fetch_channel(int(channel_id))
            if channel is not None:
                ctx_source = _FakeOnlineMessage(channel, bot)
            else:
                print(f"[onBotOnline Event Error] channel '{channel_id}' not found")
        except (ValueError, discord.HTTPException, discord.Forbidden, discord.NotFound) as e:
            print(f"[onBotOnline Event Error] invalid channel '{channel_id}': {e}")

    try:
        await run_script(ctx_source, bot, script_text, is_event=True)
    except Exception as e:
        print(f"[onBotOnline Event Error] : {e}")