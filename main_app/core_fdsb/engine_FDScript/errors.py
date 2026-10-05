# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/errors.py


class StopExecution(Exception):
    pass

class _FDError(Exception):
    _category: str = "Error"
    _icon: str = "❌"
    def __init__(self, message: str):
        super().__init__(message)
        self.msg = message

class FDSyntaxError(_FDError):
    _category = "Syntax Error"
    _icon = "🔴"

class FDLogicError(_FDError):
    _category = "Logic Error"
    _icon = "🟠"

class FDRuntimeError(_FDError):
    _category = "Runtime Error"
    _icon = "🟡"

class FDEnvironmentError(_FDError):
    _category = "Environment Error"
    _icon = "🔵"

class FDAbortScript(Exception):
    pass

async def _send_error(ch, error) -> None:
    ctx = getattr(ch, 'ctx', None)
    if ctx is not None and getattr(ctx, 'suppress_errors', False):
        ctx.log_event(f"[suppressed] {error._category}: {error.msg}")
        custom_msg = getattr(ctx, 'suppress_errors_message', None)
        if custom_msg and ch is not None:
            try:
                await ch.send(custom_msg)
            except Exception as e:
                print(f"[FDScript Error Logger] Failed to send suppressed-error message: {e}")
        raise FDAbortScript()

    if ch is not None:
        try:
            await ch.send(f"{error._icon} **{error._category}** — {error.msg}")
        except Exception as e:
            print(f"[FDScript Error Logger] Failed to send error to channel: {e}")
    else:
        print(f"[FDScript Console Error] {error._category}: {error.msg}")
    raise FDAbortScript()
