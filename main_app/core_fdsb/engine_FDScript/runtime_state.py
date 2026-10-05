# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/runtime_state.py

_BOT_START_TIME: float = 0.0

_inline_resolver = None 

def set_bot_start_time(t: float):
    global _BOT_START_TIME
    _BOT_START_TIME = t

def register_inline_resolver(fn):
    global _inline_resolver
    _inline_resolver = fn
