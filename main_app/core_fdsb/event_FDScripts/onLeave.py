# main_app/core_fdsb/event_FDScripts/onLeave.py
import discord
from main_app.core_fdsb.FDScript import Interpreter
from main_app.core_fdsb.event_FDScripts._event_context import build_member_context


async def handle_event(member: discord.Member, bot: discord.Client, script_text: str):
    from main_app.core_fdsb.Server import set_fgs_state, STATE_SYNCING
    set_fgs_state(STATE_SYNCING)

    interpreter = Interpreter(script_text)
    ctx = build_member_context(bot, member, script_text, "$onLeave")
    await interpreter.run(ctx)