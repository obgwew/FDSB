# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/commands_view.py . migrated to Flet 0.85.2+ / v1 API

import os
import flet as ft
import re
import asyncio

from main_app.theme.theme_engine import ThemeEngine
from main_app.langs.translations import Translations
from main_app.settings import get_current_lang, is_mobile

try:
    from main_app.core_fdsb.FDCore import (
        KNOWN_COMMANDS, CONTROL_FLOW_COMMANDS, FUNCTION_COMMANDS,
    )
except ImportError:
    KNOWN_COMMANDS = set()
    CONTROL_FLOW_COMMANDS = {
        "if", "elif", "else", "endif", "while", "endwhile", "for", "endfor",
        "break", "return", "and", "or", "onlyIf", "onlyAdmin", "log"
    }
    FUNCTION_COMMANDS = {"func", "endfunc", "call"}

try:
    from main_app.core_fdsb.local_server import EVENT_PREFIXES
except ImportError:
    EVENT_PREFIXES = {'$onJoined', '$onLeave', '$alwaysReply', '$onInteraction'}
    
def _t(key: str) -> str:
    return Translations.get(key, get_current_lang())

def _t_or(key: str, fallback: str = '') -> str:
    try:
        val = _t(key)
    except Exception:
        val = None
    if not val or val == key:
        return fallback
    return val

def _ar(text: str) -> str:
    return text

def _c(key: str) -> str:
    return ThemeEngine.hex(key)

_HL_FUNC_COLOR    = '#F1C40F'
_HL_FONT_SIZE     = 16
_HL_LINE_HEIGHT   = 1.45
_HL_FONT_FAMILY   = "Consolas, 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', monospace"
_HL_FONT_WEIGHT   = ft.FontWeight.W_400
_HL_LETTER_SPACE  = 0

_MOBILE_MIN_LINES = 14
_DESKTOP_MIN_LINES = 18

_MAX_SYNTAX_CHARS = 2000

_COMPILED_PATTERN = None

def _get_compiled_pattern():
    global _COMPILED_PATTERN
    if _COMPILED_PATTERN is not None:
        return _COMPILED_PATTERN

    known_cmds = set(KNOWN_COMMANDS) if KNOWN_COMMANDS else set()
    control_flow_escaped = '|'.join(sorted(CONTROL_FLOW_COMMANDS, key=len, reverse=True))
    func_escaped = '|'.join(sorted(FUNCTION_COMMANDS - CONTROL_FLOW_COMMANDS, key=len, reverse=True)) if FUNCTION_COMMANDS else ''
    known_escaped = '|'.join(sorted(known_cmds - CONTROL_FLOW_COMMANDS - FUNCTION_COMMANDS, key=len, reverse=True))

    control_part = rf'\$(?:{control_flow_escaped})\b' if control_flow_escaped else r'(?!x)x'
    func_part    = rf'\$(?:{func_escaped})\b'         if func_escaped        else r'(?!x)x'
    known_part   = rf'\$(?:{known_escaped})\b'        if known_escaped       else r'(?!x)x'

    master_pattern = (
        r'(?P<comment>#.*)'
        r'|(?P<string>".*?"|\'.*?\')'
        rf'|(?P<control>{control_part})'
        rf'|(?P<func>{func_part})'
        rf'|(?P<known>{known_part})'
        r'|(?P<token>\$\w*)'
        r'|(?P<punct>[\[\];])'
        r'|(?P<text>[^#"\'$\[\];\n]+)'
        r'|(?P<nl>\n)'
    )
    _COMPILED_PATTERN = re.compile(master_pattern)
    return _COMPILED_PATTERN


def _bot_root_from_dir(bot_dir: str) -> str:
    return os.path.dirname(os.path.abspath(bot_dir))

def _cmds_dir(bot_dir: str) -> str:
    return os.path.join(_bot_root_from_dir(bot_dir), 'bot_commands')

def _get_event_prefixes() -> set[str]:
    return EVENT_PREFIXES

def _is_event_prefix(prefix: str) -> bool:
    clean_prefix = prefix.strip().split('[')[0]
    return clean_prefix in _get_event_prefixes()

def _events_dir(bot_dir: str) -> str:
    return os.path.join(_bot_root_from_dir(bot_dir), 'bot_events')

def _ensure_events_dir(bot_dir: str) -> str:
    path = _events_dir(bot_dir)
    os.makedirs(path, exist_ok=True)
    return path

def _ensure_cmds_dir(bot_dir: str) -> str:
    path = _cmds_dir(bot_dir)
    os.makedirs(path, exist_ok=True)
    return path

def _parse_cmd_file(path: str) -> dict:
    name = os.path.splitext(os.path.basename(path))[0]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
    except Exception:
        return {'name': name, 'prefix': '', 'content': '', 'path': path}

    prefix  = ''
    content = raw
    if raw.startswith('#PREFIX:'):
        nl      = raw.find('\n')
        prefix  = raw[8:nl].strip() if nl != -1 else raw[8:].strip()
        content = raw[nl + 1:] if nl != -1 else ''

    return {'name': name, 'prefix': prefix, 'content': content, 'path': path}

def _list_cmd_files(bot_dir: str) -> list:
    results = []

    for folder, is_event in [(_cmds_dir(bot_dir), False), (_events_dir(bot_dir), True)]:
        if not os.path.isdir(folder):
            continue
        try:
            for f in os.listdir(folder):
                if not f.endswith('.fds'):
                    continue
                parsed = _parse_cmd_file(os.path.join(folder, f))
                parsed['is_event'] = is_event
                results.append(parsed)
        except Exception:
            pass

    return sorted(results, key=lambda c: c['name'].lower())

def _cmd_file_exists(bot_dir: str, safe_name: str, exclude_path: str = '') -> bool:
    exclude_abs = os.path.abspath(exclude_path) if exclude_path else ''
    for folder in (_cmds_dir(bot_dir), _events_dir(bot_dir)):
        candidate = os.path.join(folder, f'{safe_name}.fds')
        if os.path.isfile(candidate) and os.path.abspath(candidate) != exclude_abs:
            return True
    return False

def _write_cmd_file(bot_dir: str, name: str, prefix: str,
                    content: str, old_path: str = '') -> str:
    safe     = ''.join(c for c in name if c.isalnum() or c in ('-', '_')).strip() or 'command'

    if _is_event_prefix(prefix):
        dest_dir = _ensure_events_dir(bot_dir)
        folder_label = 'bot_events'
    else:
        dest_dir = _ensure_cmds_dir(bot_dir)
        folder_label = 'bot_commands'

    new_path = os.path.join(dest_dir, f'{safe}.fds')

    if old_path and os.path.abspath(old_path) != os.path.abspath(new_path):
        if os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass

    with open(new_path, 'w', encoding='utf-8') as f:
        f.write(f'#PREFIX:{prefix}\n{content}')

    print(f'[Commands] saved → {new_path}  ({folder_label})')
    return new_path

def _remove_cmd_file(path: str):
    if os.path.isfile(path):
        try:
            os.remove(path)
            print(f'[Commands] deleted → {path}')
        except Exception as e:
            print(f'[Commands] delete error: {e}')

def _btn_style(bg: str, fg: str = '#FFFFFF',
               padding: ft.Padding = None) -> ft.ButtonStyle:
    style = ft.ButtonStyle(bgcolor=bg, color=fg)
    if padding:
        style.padding = padding
    return style

def _border_all(width: float, color: str) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)

def _confirm_delete(page: ft.Page, item_name: str, on_confirm: callable):
    def _do(_):
        page.pop_dialog()
        on_confirm()

    def _cancel(_):
        page.pop_dialog()

    formatted_msg = _t('delete_confirm').replace('{item_name}', item_name)

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=_c('card_bg'),
        shape=ft.RoundedRectangleBorder(radius=16),
        title=ft.Row(
            [
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=_c('danger'), size=22),
                ft.Text(_t('delete_q'), weight=ft.FontWeight.BOLD,
                        color=_c('text'), size=16),
            ],
            spacing=8,
        ),
        content=ft.Text(
            _ar(formatted_msg),
            color=_c('text_dim'),
            size=13,
        ),
        actions=[
            ft.TextButton(
                content=ft.Text(_t('cancel'), color=_c('text_dim')),
                on_click=_cancel,
            ),
            ft.FilledButton(
                content=ft.Row(
                    [ft.Icon(ft.Icons.DELETE_FOREVER_ROUNDED, color='#FFFFFF', size=16),
                     ft.Text(_t('delete'), color='#FFFFFF', weight=ft.FontWeight.BOLD)],
                    spacing=6, tight=True,
                ),
                on_click=_do,
                style=ft.ButtonStyle(
                    bgcolor=_c('danger'),
                    color='#FFFFFF',
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding(left=14, top=8, right=14, bottom=8),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.show_dialog(dlg)

def _confirm_unsaved(page: ft.Page, on_save: callable, on_discard: callable,
                      on_cancel: callable = None):
    def _do_save(_):
        page.pop_dialog()
        on_save()

    def _do_discard(_):
        page.pop_dialog()
        on_discard()

    def _cancel(_):
        page.pop_dialog()
        on_cancel and on_cancel()

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=_c('card_bg'),
        shape=ft.RoundedRectangleBorder(radius=16),
        title=ft.Row(
            [
                ft.Icon(ft.Icons.EDIT_NOTE_ROUNDED, color=_c('warning'), size=22),
                ft.Text(_t('unsaved_title'), weight=ft.FontWeight.BOLD,
                        color=_c('text'), size=16),
            ],
            spacing=8,
        ),
        content=ft.Text(
            _t('unsaved_body'),
            color=_c('text_dim'),
            size=13,
        ),
        actions=[
            ft.TextButton(
                content=ft.Text(_t('cancel'), color=_c('text_dim')),
                on_click=_cancel,
            ),
            ft.TextButton(
                content=ft.Text(_t('discard'), color=_c('danger')),
                on_click=_do_discard,
            ),
            ft.FilledButton(
                content=ft.Row(
                    [ft.Icon(ft.Icons.SAVE_OUTLINED, color='#FFFFFF', size=16),
                     ft.Text(_t('save'), color='#FFFFFF', weight=ft.FontWeight.BOLD)],
                    spacing=6, tight=True,
                ),
                on_click=_do_save,
                style=ft.ButtonStyle(
                    bgcolor=_c('success'),
                    color='#FFFFFF',
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding(left=14, top=8, right=14, bottom=8),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.show_dialog(dlg)


class CommandEditorView:

    def __init__(self, page: ft.Page, on_back=None, on_saved=None, on_wiki_request=None):
        self._page     = page
        self._on_back  = on_back
        self._on_saved = on_saved
        self._on_wiki_request = on_wiki_request
        self._bot_dir  = ''
        self._cmd_path = ''
        
        self._last_lines_count = 1
        self._body_col = None
        self._is_mobile = is_mobile()

        self._syntax_enabled = True

        self._is_dirty = False
        self._snapshot: dict = {}

        self._hl_colors = {}
        self._kb_spacer = ft.Container(height=0, visible=True)
        self._last_kb_inset = 0.0
        self._media_handler_bound = False

        min_lines = _MOBILE_MIN_LINES if self._is_mobile else _DESKTOP_MIN_LINES

        self._name_field = ft.TextField(
            key="cmd_name_field",
            label=_t('name_label'),
            hint_text=_t('commands_label'),
            dense=True,
            border_color=_c('card_border'),
            focused_border_color=_c('accent'),
            label_style=ft.TextStyle(color=_c('text_dim'), size=11),
            text_style=ft.TextStyle(color=_c('text'), size=12),
            cursor_color=_c('accent'),
            bgcolor=_c('card_bg'),
            expand=True,
            keyboard_type=ft.KeyboardType.TEXT,
            enable_suggestions=True,
            on_change=self._mark_dirty,
        )
        self._prefix_field = ft.TextField(
            label=_t('prefix_label'),
            hint_text=_t('prefix_hint'),
            dense=True,
            border_color=_c('card_border'),
            focused_border_color=_c('accent'),
            label_style=ft.TextStyle(color=_c('text_dim'), size=11),
            text_style=ft.TextStyle(color=_c('text'), size=12),
            cursor_color=_c('accent'),
            bgcolor=_c('card_bg'),
            keyboard_type=ft.KeyboardType.TEXT,
            enable_suggestions=True,
            on_change=self._on_prefix_change,
            expand=True,
        )

        self._lines_lbl = ft.Text('0', size=18, weight=ft.FontWeight.BOLD, color=_c('text'))
        self._chars_lbl = ft.Text('0', size=18, weight=ft.FontWeight.BOLD, color=_c('text'))

        self._syntax_switch_label = ft.Text(
            _t('syntax_color_label'),
            size=10,
            weight=ft.FontWeight.BOLD,
            color=_c('text_dim'),
        )
        self._syntax_switch = ft.Switch(
            value=True,
            active_color=_c('accent'),
            scale=0.80,
            tooltip="Syntax Switch",
            on_change=self._on_syntax_switch_change,
        )

        self._syntax_warning_banner = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=16, color=_c('warning')),
                    ft.Text(
                        _t('syntax_warn_banner'),
                        size=11,
                        color=_c('warning'),
                        weight=ft.FontWeight.W_500,
                        expand=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=_c('warning') + '15',
            border=ft.Border(
                left=ft.BorderSide(3, _c('warning')),
                top=ft.BorderSide(1, _c('warning') + '35'),
                right=ft.BorderSide(1, _c('warning') + '35'),
                bottom=ft.BorderSide(1, _c('warning') + '35'),
            ),
            border_radius=8,
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            visible=False, 
        )

        self._line_nums = ft.Text(
            "1",
            size=_HL_FONT_SIZE,
            font_family=_HL_FONT_FAMILY,
            color=_c('text_dim'),
            text_align=ft.TextAlign.RIGHT,
            style=ft.TextStyle(
                height=_HL_LINE_HEIGHT,
                font_family=_HL_FONT_FAMILY,
                size=_HL_FONT_SIZE,
                weight=_HL_FONT_WEIGHT,
                letter_spacing=_HL_LETTER_SPACE,
            )
        )

        self._highlighter = ft.Text(
            font_family=_HL_FONT_FAMILY,
            size=_HL_FONT_SIZE,
            selectable=False,
            text_align=ft.TextAlign.LEFT,
            rtl=False,  
            style=ft.TextStyle(
                height=_HL_LINE_HEIGHT,
                font_family=_HL_FONT_FAMILY,
                size=_HL_FONT_SIZE,
                weight=_HL_FONT_WEIGHT,
                letter_spacing=_HL_LETTER_SPACE,
            ),
        )

        self._code_edit = ft.TextField(
            multiline=True,
            text_align=ft.TextAlign.LEFT,         
            rtl=False,                  
            dense=True,    
            expand=True,                   
            text_style=ft.TextStyle(
                color=ft.Colors.TRANSPARENT,
                font_family=_HL_FONT_FAMILY,
                size=_HL_FONT_SIZE,
                height=_HL_LINE_HEIGHT,
                weight=_HL_FONT_WEIGHT,
                letter_spacing=_HL_LETTER_SPACE,
            ),
            cursor_color=_c('syntax_cmd'),
            cursor_width=2,
            border=ft.InputBorder.NONE,
            content_padding=0,                 
            min_lines=min_lines,
            max_lines=99999,
            keyboard_type=ft.KeyboardType.MULTILINE,
            enable_suggestions=True,
            autocorrect=False,            
            smart_dashes_type=False,
            smart_quotes_type=False,
            on_change=self._on_code_change,
            on_focus=self._on_code_focus,
        )

        self._code_container = ft.Container(
            content=ft.Stack(
                controls=[
                    self._highlighter,
                    self._code_edit,
                ],
            ),
            width=1000,
            padding=8,
        )

        self._title_text = ft.Text(
            _ar('New.fds'), size=13, weight=ft.FontWeight.BOLD, color=_c('text')
        )
        
        self._dirty_dot = ft.Container(
            width=7, height=7,
            bgcolor=_c('warning'),
            border_radius=4,
            visible=False,
            tooltip=_t('unsaved_title'),
        )

        self._save_btn = ft.FilledButton(
            content=ft.Row(
                [ft.Icon(ft.Icons.SAVE_OUTLINED, color='#FFFFFF'),
                 ft.Text(_t('save'), color='#FFFFFF')],
                spacing=6, tight=True,
            ),
            on_click=self._save,
            style=_btn_style(_c('success')),
        )
        self._dest_indicator = ft.Text(
            _t('dest_cmd'),
            size=10,
            color=_c('text_dim'),
            italic=True,
        )

        ThemeEngine.subscribe(self._on_theme)

    def _on_syntax_switch_change(self, e):
        new_val = e.control.value
        current_len = len(self._code_edit.value or '')

        if new_val and current_len > _MAX_SYNTAX_CHARS:
            self._syntax_switch.value = False
            self._syntax_enabled = False
            self._syntax_switch.update()

            if self._page:
                self._page.show_dialog(
                    ft.SnackBar(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#FFFFFF", size=20),
                                ft.Text(
                                    _t('syntax_limit_refusal'),
                                    color="#FFFFFF",
                                    size=13,
                                )
                            ],
                            spacing=8,
                        ),
                        bgcolor=_c('danger'),
                        duration=3500,
                    )
                )
                self._page.update()
            return

        self._syntax_enabled = new_val
        self._update_syntax_mode()

    def _update_syntax_mode(self):
        current_len = len(self._code_edit.value or '')
        if self._syntax_enabled:
            self._highlighter.visible = True
            self._code_edit.text_style.color = ft.Colors.TRANSPARENT
            self._syntax_warning_banner.visible = (current_len > _MAX_SYNTAX_CHARS)
            self._apply_highlights()
        else:
            self._highlighter.visible = False
            self._highlighter.spans = []
            self._code_edit.text_style.color = _c('text')
            self._syntax_warning_banner.visible = False

        if self._page:
            self._page.update()

    def _set_name_error(self):
        self._name_field.error                = _t('name_required')
        self._name_field.border_color         = _c('danger')
        self._name_field.focused_border_color = _c('danger')

    def _set_name_taken_error(self):
        self._name_field.error                = _t_or('name_taken')
        self._name_field.border_color         = _c('danger')
        self._name_field.focused_border_color = _c('danger')

    def _clear_name_error(self):
        if self._name_field.error:
            self._name_field.error                = None
            self._name_field.border_color         = _c('card_border')
            self._name_field.focused_border_color = _c('accent')

    async def _scroll_to_name_error_async(self):
        if self._body_col is not None:
            try:
                await self._body_col.scroll_to(
                    scroll_key="cmd_name_field", duration=300,
                )
            except Exception:
                pass
        try:
            await self._name_field.focus()
        except Exception:
            pass

    def _scroll_to_name_error(self):
        if self._page:
            self._page.run_task(self._scroll_to_name_error_async)

    def _mark_dirty(self, e=None):
        name_error_was_cleared = False
        if e is not None and e.control is self._name_field and self._name_field.error:
            self._clear_name_error()
            name_error_was_cleared = True

        cur = {
            'name':    self._name_field.value   or '',
            'prefix':  self._prefix_field.value or '',
            'content': self._code_edit.value    or '',
        }
        dirty = cur != self._snapshot
        state_changed = dirty != self._is_dirty
        if state_changed:
            self._is_dirty          = dirty
            self._dirty_dot.visible = dirty

        if (state_changed or name_error_was_cleared) and self._page:
            self._page.update()

    def _clear_dirty(self):
        self._snapshot = {
            'name':    self._name_field.value   or '',
            'prefix':  self._prefix_field.value or '',
            'content': self._code_edit.value    or '',
        }
        self._is_dirty          = False
        self._dirty_dot.visible = False

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    def guard_navigation(self, on_proceed: callable, on_cancel: callable = None):
        if self._is_dirty:
            _confirm_unsaved(
                self._page,
                on_save=lambda: self._save_then_proceed(on_proceed, on_cancel),
                on_discard=lambda: self._discard_and_proceed(on_proceed),
                on_cancel=on_cancel,
            )
        else:
            on_proceed and on_proceed()

    def _save_then_proceed(self, on_proceed, on_cancel: callable = None):
        if self._save(None):
            on_proceed and on_proceed()
        else:
            on_cancel and on_cancel()

    def _discard_and_proceed(self, on_proceed):
        self._clear_dirty()
        on_proceed and on_proceed()

    def _request_back(self, _):
        self.guard_navigation(self._on_back)

    def _on_theme(self, data: dict):
        global _COMPILED_PATTERN
        _COMPILED_PATTERN = None

        g = lambda k, default='#888888': data.get(k, default)

        for field in (self._name_field, self._prefix_field):
            field.border_color         = g('card_border')
            field.focused_border_color = g('syntax_cmd')
            field.bgcolor              = g('card_bg')
            field.cursor_color         = g('syntax_cmd')
            field.label_style          = ft.TextStyle(color=g('text_dim'), size=11)
            field.text_style           = ft.TextStyle(color=g('text'), size=12)

        self._code_edit.cursor_color = g('syntax_cmd')
        if not self._syntax_enabled:
            self._code_edit.text_style.color = g('text')

        self._lines_lbl.color           = g('text')
        self._chars_lbl.color           = g('text')
        self._syntax_switch_label.color = g('text_dim')
        self._syntax_switch_label.value = _t('syntax_color_label')
        self._syntax_switch.active_color = g('accent')
        self._title_text.color          = g('text')
        self._save_btn.style            = _btn_style(g('success'))
        self._dirty_dot.bgcolor         = g('warning')
        self._line_nums.color           = g('text_dim')

        self._syntax_warning_banner.bgcolor = g('warning') + '15'
        self._syntax_warning_banner.border = ft.Border(
            left=ft.BorderSide(3, g('warning')),
            top=ft.BorderSide(1, g('warning') + '35'),
            right=ft.BorderSide(1, g('warning') + '35'),
            bottom=ft.BorderSide(1, g('warning') + '35'),
        )

        if self._name_field.error:
            err_color = g('danger', '#FC2323')
            self._name_field.border_color         = err_color
            self._name_field.focused_border_color = err_color

        self._hl_colors = {
            'base':    g('success',              '#2ECC71'),
            'control': g('syntax_control_flow',  '#9B59B6'),
            'func':    g('syntax_func',          _HL_FUNC_COLOR),
            'known':   g('syntax_cmd',            '#3498DB'),
            'bracket': g('syntax_brackets',       '#FC2323'),
            'semi':    g('syntax_semicolon',      '#8A200D'),
            'comment': g('text_dim',              '#7F8C8D'),
        }

        if self._syntax_enabled:
            self._apply_highlights()

    def _bind_media_handler(self):
        if self._media_handler_bound or not self._page:
            return
        try:
            if hasattr(self._page, 'on_media_change'):
                prev = getattr(self._page, 'on_media_change', None)

                def _combined(e):
                    if callable(prev):
                        try:
                            prev(e)
                        except Exception:
                            pass
                    self._on_media_change(e)

                self._page.on_media_change = _combined
                self._media_handler_bound = True
        except Exception as ex:
            print(f'[Commands] media handler bind failed: {ex}')

    def _get_kb_inset(self) -> float:
        try:
            media = getattr(self._page, 'media', None)
            if media is None:
                return 0.0
            insets = getattr(media, 'view_insets', None)
            if insets is None:
                return 0.0
            bottom = getattr(insets, 'bottom', 0) or 0
            return float(bottom)
        except Exception:
            return 0.0

    def _apply_kb_inset(self, inset: float = None):
        if inset is None:
            inset = self._get_kb_inset()

        if abs(inset - self._last_kb_inset) < 1.0:
            return

        self._last_kb_inset = inset
        extra = 24.0 if inset > 0 else 0.0
        target = max(0.0, inset + extra)

        self._kb_spacer.height = target

        if self._page:
            self._page.update()

        if inset > 0 and self._page:
            self._page.run_task(self._scroll_to_editor_async)

    def _on_media_change(self, e=None):
        self._apply_kb_inset()

    def build(self) -> ft.Control:
        self._bind_media_handler()

        header = ft.Container(
            content=ft.Row(
                [
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK_ROUNDED,
                        icon_color=_c('text_on_accent'),
                        bgcolor=_c('accent'),
                        on_click=self._request_back,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                        icon_size=16,
                    ),
                    ft.Text(_t('commands_slash'), size=13, color=_c('text_dim')),
                    self._title_text,
                    self._dirty_dot,
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            height=46,
        )

        stats_col = ft.Column(
            [
                _stat_col(_t('total_lines'), self._lines_lbl),
                _stat_col(_t('total_text'),  self._chars_lbl),
            ],
            spacing=3,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        switch_block = ft.Column(
            [
                self._syntax_switch_label,
                self._syntax_switch,
            ],
            spacing=1,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        side_controls = ft.Row(
            [
                switch_block, 
                ft.Container(width=1, height=44, bgcolor=_c('card_border')),
                stats_col,    
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        wiki_shortcut_btn = ft.IconButton(
            icon=ft.Icons.MENU_BOOK_ROUNDED,
            icon_color=_c('accent'),
            tooltip="Wiki: Events / ويكي الأحداث",
            on_click=lambda _: self._on_wiki_request() if self._on_wiki_request else None,
            icon_size=20,
        )

        prefix_row = ft.Row(
            [
                self._prefix_field,
                wiki_shortcut_btn
            ],
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        info_card = ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [self._name_field, prefix_row, self._dest_indicator],
                        spacing=6,
                        expand=True,
                    ),
                    side_controls,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=_c('card_bg'),
            border=_border_all(1, _c('card_border')),
            border_radius=12,
            padding=ft.Padding(left=10, right=10, top=10, bottom=10),
        )

        code_scroll_area = ft.Row(
            controls=[self._code_container],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        editor_area = ft.Container(
            key="cmd_editor_area",
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=self._line_nums,
                        padding=ft.Padding(left=8, right=8, top=8, bottom=8),
                        bgcolor=_c('card_bg'),
                        border=ft.Border(right=ft.BorderSide(1, _c('card_border'))),
                    ),
                    code_scroll_area,
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            bgcolor=_c('card_bg'),
            border=_border_all(1, _c('card_border')),
            border_radius=10,
        )

        body_col = ft.Column(
            [
                ft.Text(_t('info_command'), size=11, weight=ft.FontWeight.BOLD, color=_c('text_dim')),
                info_card,
                self._syntax_warning_banner,
                ft.Text(_t('command_editor'), size=12, weight=ft.FontWeight.BOLD, color=_c('text')),
                editor_area,
                self._kb_spacer,
                ft.Container(height=70), 
            ],
            spacing=10,
            expand=True,
            scroll=ft.ScrollMode.ADAPTIVE,
        )
        self._body_col = body_col

        self._apply_kb_inset()

        return ft.Column(
            [
                header,
                ft.Stack(
                    [
                        ft.Container(
                            content=body_col,
                            padding=ft.Padding(left=12, right=12, top=8, bottom=0),
                            expand=True,
                        ),
                        ft.Container(
                            content=self._save_btn,
                            bottom=16,
                            right=16,
                            alignment=ft.Alignment(0, 0),
                        ),
                    ],
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )

    def _on_prefix_change(self, e):
        prefix = (e.control.value or '').strip()
        self._update_dest_indicator(prefix)
        self._mark_dirty()

    def _update_dest_indicator(self, prefix: str):
        if _is_event_prefix(prefix):
            self._dest_indicator.value = _t('dest_event')
            self._dest_indicator.color = '#22B9FF'
        else:
            self._dest_indicator.value = _t('dest_cmd')
            self._dest_indicator.color = _c('text_dim')
        if self._page:
            self._page.update()

    async def _scroll_to_editor_async(self):
        if self._body_col is not None:
            try:
                await self._body_col.scroll_to(
                    scroll_key="cmd_editor_area", duration=250,
                )
            except Exception:
                pass

    def _on_code_focus(self, e):
        self._apply_kb_inset()
        if self._page:
            self._page.run_task(self._scroll_to_editor_async)

    def _apply_highlights(self):
        if not self._syntax_enabled:
            return

        try:
            text = self._code_edit.value or ''

            if not text:
                self._highlighter.spans = []
                self._highlighter.value = ''
                if self._highlighter.page:
                    self._highlighter.update()
                return

            pattern = _get_compiled_pattern()
            colors     = self._hl_colors
            base_color = colors.get('base', '#2ECC71')

            def _make_span(val: str, col: str) -> ft.TextSpan:
                return ft.TextSpan(
                    val,
                    ft.TextStyle(
                        color=col,
                        size=_HL_FONT_SIZE,
                        height=_HL_LINE_HEIGHT,
                        font_family=_HL_FONT_FAMILY,
                        weight=_HL_FONT_WEIGHT,
                        letter_spacing=_HL_LETTER_SPACE,
                    ),
                )

            raw_spans = []
            for match in pattern.finditer(text):
                val = match.group()
                grp = match.lastgroup

                if grp == 'comment':   col = colors.get('comment', base_color)
                elif grp == 'string':  col = colors.get('string', base_color)
                elif grp == 'control': col = colors.get('control', base_color)
                elif grp == 'func':    col = colors.get('func', _HL_FUNC_COLOR)
                elif grp == 'known':   col = colors.get('known', base_color)
                elif grp == 'punct':
                    col = colors.get('semi', base_color) if val == ';' else colors.get('bracket', base_color)
                else:
                    col = base_color

                if raw_spans and raw_spans[-1][1] == col:
                    raw_spans[-1] = (raw_spans[-1][0] + val, col)
                else:
                    raw_spans.append((val, col))

            self._highlighter.spans = [_make_span(v, c) for v, c in raw_spans]
            if self._highlighter.page:
                self._highlighter.update()

        except Exception:
            pass

    def _on_code_change(self, e):
        value = e.control.value or ''
        lines = value.count('\n') + 1
        current_len = len(value)
        
        if lines != self._last_lines_count:
            self._last_lines_count = lines
            self._lines_lbl.value = str(lines)
            self._line_nums.value = '\n'.join(str(i) for i in range(1, lines + 1))
            if self._line_nums.page:
                self._line_nums.update()
            if self._lines_lbl.page:
                self._lines_lbl.update()

        self._chars_lbl.value = str(current_len)
        if self._chars_lbl.page:
            self._chars_lbl.update()

        split_lines = value.split('\n') if value else ['']
        max_line_len = max((len(l) for l in split_lines), default=0)
        dynamic_width = max(1000.0, float((max_line_len + 20) * 11.5))
        if dynamic_width != self._code_container.width:
            self._code_container.width = dynamic_width
            if self._code_container.page:
                self._code_container.update()

        if not self._is_dirty:
            self._is_dirty = True
            self._dirty_dot.visible = True
            if self._dirty_dot.page:
                self._dirty_dot.update()

        should_show_banner = (current_len > _MAX_SYNTAX_CHARS) and self._syntax_enabled
        if self._syntax_warning_banner.visible != should_show_banner:
            self._syntax_warning_banner.visible = should_show_banner
            if self._syntax_warning_banner.page:
                self._syntax_warning_banner.update()

        if self._syntax_enabled:
            self._apply_highlights()

        if self._is_mobile:
            self._apply_kb_inset()

    def load(self, bot_dir: str, cmd_data: dict = None):
        self._bot_dir  = bot_dir
        self._cmd_path = cmd_data.get('path', '') if cmd_data else ''

        if cmd_data:
            self._name_field.value   = cmd_data.get('name', '')
            self._prefix_field.value = cmd_data.get('prefix', '')
            self._code_edit.value    = cmd_data.get('content', '')
            self._title_text.value   = _ar(cmd_data.get('name', 'command') + '.fds')
        else:
            self._name_field.value   = ''
            self._prefix_field.value = ''
            self._code_edit.value    = ''
            self._title_text.value   = _ar('New.fds')

        self._clear_name_error()

        content = self._code_edit.value or ''
        lines   = content.count('\n') + 1
        current_len = len(content)
        self._last_lines_count = lines
        self._lines_lbl.value = str(lines)
        self._chars_lbl.value = str(current_len)

        self._line_nums.value = '\n'.join(str(i) for i in range(1, lines + 1))

        split_lines = content.split('\n') if content else ['']
        max_line_len = max((len(l) for l in split_lines), default=0)
        self._code_container.width = max(1000.0, float((max_line_len + 20) * 11.5))

        self._update_dest_indicator((self._prefix_field.value or '').strip())
        self._clear_dirty()

        if current_len > _MAX_SYNTAX_CHARS:
            self._syntax_enabled = False
            self._syntax_switch.value = False
            self._syntax_warning_banner.visible = False
        else:
            self._syntax_enabled = True
            self._syntax_switch.value = True
            self._syntax_warning_banner.visible = False

        if self._syntax_enabled:
            self._highlighter.visible = True
            self._code_edit.text_style.color = ft.Colors.TRANSPARENT
            self._apply_highlights()
        else:
            self._highlighter.visible = False
            self._highlighter.spans = []
            self._code_edit.text_style.color = _c('text')

        self._last_kb_inset = -1
        self._apply_kb_inset(0)

    def _save(self, _) -> bool:
        name    = (self._name_field.value or '').strip()
        prefix  = (self._prefix_field.value or '').strip()
        content = self._code_edit.value or ''

        if not name:
            self._set_name_error()
            if self._page:
                self._page.update()
            self._scroll_to_name_error()
            return False

        safe_name = ''.join(c for c in name if c.isalnum() or c in ('-', '_')).strip() or 'command'

        if _cmd_file_exists(self._bot_dir, safe_name, self._cmd_path):
            self._set_name_taken_error()
            if self._page:
                self._page.update()
            self._scroll_to_name_error()
            return False

        self._clear_name_error()

        self._cmd_path = _write_cmd_file(
            self._bot_dir, name, prefix, content, self._cmd_path
        )

        self._title_text.value = _ar(name + '.fds')
        self._clear_dirty()

        if self._page:
            self._page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(_t('saved_successfully'), color='#FFFFFF'),
                    bgcolor=_c('success'),
                    duration=2000,
                )
            )
            self._page.update()

        if callable(self._on_saved):
            self._on_saved()

        return True


class CommandsListView:

    def __init__(self, page: ft.Page, on_open=None):
        self._page     = page
        self._on_open  = on_open
        self._bot_dir  = ''
        self._all_cmds = []
        self._busy     = False

        self._count_label = ft.Text(
            value="",
            size=11,
            color=_c('text_dim'),
        )

        self._search_field = ft.TextField(
            hint_text=_t('search'),
            height=40,
            width=180,
            content_padding=ft.Padding(left=10, right=10, top=0, bottom=0),
            bgcolor=_c('card_bg'),
            border_color=_c('card_border'),
            border_radius=8,
            enable_suggestions=True,
            on_change=self._on_search,
        )
        self._list_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

        ThemeEngine.subscribe(self._on_theme)

    def _update_cmds_count(self):
        count = len(self._all_cmds)
        self._count_label.value = _t('total_cmds_count').format(count=count)

    def _on_theme(self, data: dict):
        g = lambda k: data.get(k, '#888888')
        self._count_label.color                 = g('text_dim')
        self._search_field.border_color         = g('card_border')
        self._search_field.focused_border_color = g('accent')
        self._search_field.bgcolor              = g('card_bg')
        self._search_field.cursor_color         = g('accent')
        if self._bot_dir:
            self._render(self._all_cmds)
        if hasattr(self, '_page') and self._page:
            self._page.update()

    def build(self) -> ft.Control:
        header = ft.Container(
            content=ft.Column(
                [
                    self._count_label,
                    ft.Row(
                        [
                            ft.Text(_t('commands'), size=15,
                                    weight=ft.FontWeight.BOLD, color=_c('text')),
                            self._search_field,
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=2,
            ),
            padding=ft.Padding(left=12, right=12, top=6, bottom=6),
            height=66,
        )

        fab = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            bgcolor=_c('accent'),
            foreground_color=_c('text_on_accent'),
            on_click=lambda _: self._on_open and self._on_open(None),
            mini=True,
        )

        return ft.Column(
            [
                header,
                ft.Container(
                    content=ft.Stack(
                        [
                            ft.Container(
                                content=self._list_col,
                                padding=ft.Padding(left=12, right=12, top=8, bottom=0),
                                expand=True,
                            ),
                            ft.Container(
                                content=fab,
                                bottom=16,
                                right=16,
                                width=44,
                                height=44,
                                alignment=ft.Alignment(0, 0),
                            ),
                        ],
                        expand=True,
                    ),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )

    def load(self, bot_dir: str):
        self._bot_dir  = bot_dir
        self._list_col.controls.clear()
        self._list_col.controls.append(
            ft.Container(
                content=ft.ProgressRing(color=_c('accent')),
                alignment=ft.Alignment(0, 0),
                padding=ft.Padding(0, 40, 0, 0)
            )
        )
        self._count_label.value = _t('loading')
        if self._page:
            self._page.update()

        self._page.run_task(self._async_load_task)

    async def _async_load_task(self, *args):
        loop = asyncio.get_event_loop()
        self._all_cmds = await loop.run_in_executor(None, _list_cmd_files, self._bot_dir)
        
        self._update_cmds_count()
        self._render(self._all_cmds)
        if self._page:
            self._page.update()

    def _on_search(self, e):
        q        = (e.control.value or '').strip().lower()
        filtered = self._all_cmds if not q else [
            c for c in self._all_cmds
            if q in c['name'].lower() or q in c['prefix'].lower()
        ]
        self._render(filtered)

    def _render(self, cmds: list):
        self._list_col.controls.clear()
        if not cmds:
            self._list_col.controls.append(
                ft.Container(
                    content=ft.Text(
                        _t('no_cmds_hint'),
                        size=13, color=_c('text_dim'),
                        text_align=ft.TextAlign.CENTER,
                    ),
                    alignment=ft.Alignment(0, 0),
                    height=120,
                )
            )
        else:
            for idx, cmd in enumerate(cmds, start=1):
                self._list_col.controls.append(self._cmd_row(idx, cmd))
            self._list_col.controls.append(ft.Container(height=60))

        self._update_cmds_count()
        if self._page:
            self._page.update()

    def _cmd_row(self, num: int, cmd: dict) -> ft.Control:
        is_event = cmd.get('is_event', False)

        name_row = ft.Row(
            [
                ft.Text(_ar(cmd['name']), size=12,
                        weight=ft.FontWeight.BOLD,
                        color=_c('text')),
                ft.Container(
                    content=ft.Text(_t('dest_event'), size=9, color='#FFFFFF'),
                    bgcolor='#22B9FF',
                    border_radius=4,
                    padding=ft.Padding(left=5, right=5, top=1, bottom=1),
                    visible=is_event,
                ),
            ],
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Row(
            [
                ft.Text(
                    str(num), size=17, weight=ft.FontWeight.BOLD,
                    color=_c('text_dim'), width=24,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    name_row,
                                    ft.Text(_ar(cmd['prefix'] or '—'), size=11,
                                            color=_c('text_dim')),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.FilledButton(
                                content=ft.Text(_t('edit'), color=_c('text_on_accent')),
                                on_click=lambda _, c=cmd: (
                                    self._on_open and self._on_open(c)
                                ),
                                style=_btn_style(
                                    _c('accent'),
                                    _c('text_on_accent'),
                                    ft.Padding(left=10, right=10, top=4, bottom=4),
                                ),
                            ),
                            ft.FilledButton(
                                content=ft.Text(_t('del'), color='#FFFFFF'),
                                on_click=lambda _, c=cmd: self._ask_delete(c),
                                style=_btn_style(
                                    _c('danger'),
                                    '#FFFFFF',
                                    ft.Padding(left=8, right=8, top=4, bottom=4),
                                ),
                            ),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=_c('card_bg'),
                    border=_border_all(1, '#22B9FF' if is_event else _c('card_border')),
                    border_radius=10,
                    padding=ft.Padding(left=10, right=10, top=8, bottom=8),
                    expand=True,
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _ask_delete(self, cmd: dict):
        _confirm_delete(
            self._page,
            item_name=cmd.get('name', 'command'),
            on_confirm=lambda: self._do_delete(cmd),
        )

    def _do_delete(self, cmd: dict):
        _remove_cmd_file(cmd.get('path', ''))
        self.load(self._bot_dir)


class BotCommandsTab:
    def __init__(self, page: ft.Page, on_wiki_events_req=None):
        self._page        = page
        self._bot_dir     = ''
        self._in_editor   = False
        self._on_wiki_events_req = on_wiki_events_req
        
        self._list_view   = CommandsListView(page, on_open=self._open_editor)
        self._editor_view = CommandEditorView(
            page,
            on_back=self._close_editor,
            on_saved=self._on_editor_saved,
            on_wiki_request=self._on_wiki_events_req
        )
        self._container   = ft.Container(expand=True)

    def handle_back(self) -> bool:
        if self._in_editor:
            self._editor_view.guard_navigation(self._close_editor)
            return True
        return False

    def _on_editor_saved(self):
        self._list_view.load(self._bot_dir)

    def build(self) -> ft.Control:
        self._container.content = self._list_view.build()
        return self._container

    def load_bot(self, bot_dir: str):
        self._bot_dir   = bot_dir
        self._in_editor = False
        self._list_view.load(bot_dir)
        self._container.content = self._list_view.build()
        if self._page:
            self._page.update()

    def _open_editor(self, cmd_data=None):
        self._in_editor = True
        self._editor_view.load(self._bot_dir, cmd_data)
        self._container.content = self._editor_view.build()
        if self._page:
            self._page.update()

    def _close_editor(self):
        self._in_editor = False
        self._list_view.load(self._bot_dir)
        self._container.content = self._list_view.build()
        if self._page:
            self._page.update()

    def guard_tab_change(self, on_proceed: callable, on_cancel: callable = None):
        if self._in_editor and self._editor_view.is_dirty:
            def _proceed_with_refresh():
                self._list_view.load(self._bot_dir)
                self._in_editor = False
                on_proceed and on_proceed()

            self._editor_view.guard_navigation(_proceed_with_refresh, on_cancel)
        else:
            on_proceed and on_proceed()


def _stat_col(heading: str, value_ctrl: ft.Text) -> ft.Column:
    return ft.Column(
        [
            ft.Text(heading, size=9, weight=ft.FontWeight.BOLD, color=_c('text_dim')),
            value_ctrl,
        ],
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )