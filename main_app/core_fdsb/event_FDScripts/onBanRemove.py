# main_app/core_fdsb/event_FDScripts/onBanRemove.py
import discord
from main_app.core_fdsb.FDScript import Interpreter
from main_app.core_fdsb.event_FDScripts._event_context import build_ban_context


async def handle_event(guild: discord.Guild, user: discord.User | discord.Member,
                       bot: discord.Client, script_text: str) -> None:
    from main_app.core_fdsb.Server import set_fgs_state, STATE_SYNCING
    set_fgs_state(STATE_SYNCING)

    interpreter = Interpreter(script_text)
    ctx = build_ban_context(bot, guild, user, script_text, "$onBanRemove")
    await interpreter.run(ctx)