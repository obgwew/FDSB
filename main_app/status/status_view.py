# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/status_view.py — Bot Status UI (list + create/edit entry)

import flet as ft
import json
import os
from urllib.parse import urlparse

from main_app.langs.translations import Translations

# ══════════════════════════════════════════════════════════════════════════════
#  Helpers (mirrors main_app/settings.py styling helpers)
# ══════════════════════════════════════════════════════════════════════════════

def _t(key: str, lang: str) -> str:
    val = Translations.get(key, lang)
    return val if val and val != key else key


def _border_all(w: float, color: str) -> ft.Border:
    s = ft.BorderSide(w, color)
    return ft.Border(left=s, top=s, right=s, bottom=s)


def _btn_style(bg: str, fg: str = '#FFFFFF',
               padding: ft.Padding = None) -> ft.ButtonStyle:
    style = ft.ButtonStyle(bgcolor=bg, color=fg)
    if padding:
        style.padding = padding
    return style


# Fixed presence colors (Discord-style) — intentionally not theme-driven,
# same way 'discord'/'btn_invite' colors are fixed across every theme.
_PRESENCE_COLORS = {
    'online':     '#23A55A',
    'idle':       '#F0B232',
    'dnd':        '#F23F43',
    'invisible':  '#80848E',
}

# Real Discord activity types (discord.py ActivityType). 'streaming' is the
# only one Discord actually renders with a clickable link, so it's the only
# one that needs — and is allowed — a URL.
_ACTIVITY_ICONS = {
    'playing':    ft.Icons.SPORTS_ESPORTS_ROUNDED,
    'streaming':  ft.Icons.LIVE_TV_ROUNDED,
    'listening':  ft.Icons.HEADPHONES_ROUNDED,
    'watching':   ft.Icons.VISIBILITY_ROUNDED,
    'competing':  ft.Icons.EMOJI_EVENTS_ROUNDED,
}

# Loop-time unit → seconds multiplier, and the minimum allowed loop time
# expressed in seconds (a loop can never fire more often than every 12s).
_LOOP_UNIT_SECONDS = {
    'second': 1,
    'minute': 60,
    'hour':   3600,
    'day':    86400,
}
_LOOP_TIME_MIN_SECONDS = 12


# ══════════════════════════════════════════════════════════════════════════════
#  BotStatusView
# ══════════════════════════════════════════════════════════════════════════════

class BotStatusView:

    def __init__(self, page: ft.Page, theme_hex, bot_data: dict = None,
                 lang: str = 'en', on_back=None):
        self._page      = page
        self._c         = theme_hex          # callable: theme color lookup, e.g. settings._c
        self._bot_data  = bot_data or {}
        self._lang      = lang
        self._on_back   = on_back            # called when leaving this view entirely

        # Bot folder on disk, so status_config.json can be saved/loaded next
        # to config.json (see _get_token in local_server.py). Tries the
        # common key names — adjust here if settings.py uses a different one.
        self._bot_dir = (
            self._bot_data.get('dir')
            or self._bot_data.get('path')
            or self._bot_data.get('bot_dir')
            or self._bot_data.get('folder')
            or ''
        )

        self._container: ft.Container | None = None

        # ── list-screen state ───────────────────────────────────────────────
        self._status_value   = 'online'
        self._loop_unit_value = 'second'
        self._loop_time_field = ft.TextField(
            hint_text=self._tt('sv_loop_time_hint'),
            dense=True, keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            border_color=self._c('card_border'),
            focused_border_color=self._c('accent'),
            cursor_color=self._c('accent'),
            text_style=ft.TextStyle(color=self._c('text'), size=13),
            bgcolor=self._c('card_bg'),
            expand=True,
            on_change=lambda e: self._validate_loop_time(),
        )
        self._presence_checkbox = ft.Checkbox(
            value=False,
            label=self._tt('sv_activate_presence'),
            label_style=ft.TextStyle(color=self._c('text'), size=13),
            active_color=self._c('accent'),
            on_change=lambda e: self._save_status_config(),
        )
        self._entries_col = ft.Column(spacing=8)

        # demo placeholder entries — purely visual, matches the wireframe (2 rows)
        self._entries: list[dict] = [
            {'prefix': '', 'status': '', 'details': self._tt('sv_entry_details_ph')},
            {'prefix': '', 'status': '', 'details': self._tt('sv_entry_details_ph')},
        ]

        # ── editor-screen state ─────────────────────────────────────────────
        self._editing_index: int | None = None
        self._activity_type_value = 'playing'
        self._activity_dropdown = ft.Dropdown(
            value=self._activity_type_value,
            label=self._tt('sv_activity_type'),
            dense=True, border=ft.InputBorder.UNDERLINE,
            border_color=self._c('card_border'), focused_border_color=self._c('accent'),
            bgcolor=self._c('card_bg'), color=self._c('text'),
            label_style=ft.TextStyle(color=self._c('text_dim'), size=12),
            text_style=ft.TextStyle(color=self._c('text'), size=14),
            options=[
                ft.DropdownOption(key=k, text=self._activity_label(k))
                for k in ('playing', 'streaming', 'listening', 'watching', 'competing')
            ],
            on_select=self._on_activity_select,
        )
        self._edit_status_field = ft.TextField(
            label=self._tt('sv_status_field'), hint_text=self._tt('sv_status_hint'),
            dense=True, border=ft.InputBorder.UNDERLINE,
            border_color=self._c('card_border'), focused_border_color=self._c('accent'),
            cursor_color=self._c('accent'),
            label_style=ft.TextStyle(color=self._c('text_dim'), size=12),
            text_style=ft.TextStyle(color=self._c('text'), size=14),
            on_change=lambda e: self._refresh_preview(),
        )
        self._stream_url_field = ft.TextField(
            label=self._tt('sv_stream_url'), hint_text=self._tt('sv_stream_url_hint'),
            dense=True, border=ft.InputBorder.UNDERLINE,
            border_color=self._c('card_border'), focused_border_color=self._c('accent'),
            cursor_color=self._c('accent'),
            label_style=ft.TextStyle(color=self._c('text_dim'), size=12),
            text_style=ft.TextStyle(color=self._c('text'), size=14),
            keyboard_type=ft.KeyboardType.URL,
            on_change=lambda e: self._validate_stream_url(),
        )
        self._edit_details_field = ft.TextField(
            label=self._tt('sv_status_details'), hint_text=self._tt('sv_details_hint'),
            dense=True, border=ft.InputBorder.UNDERLINE,
            border_color=self._c('card_border'), focused_border_color=self._c('accent'),
            cursor_color=self._c('accent'),
            label_style=ft.TextStyle(color=self._c('text_dim'), size=12),
            text_style=ft.TextStyle(color=self._c('text'), size=14),
            on_change=lambda e: self._refresh_preview(),
        )


        self._preview_name_text   = ft.Text(self._tt('sv_name_bot'), size=15,
                                             weight=ft.FontWeight.BOLD, color='#F2F3F5')
        self._preview_status_text = ft.Text('', size=13, color='#B5BAC1')
        self._preview_activity_icon = ft.Icon(_ACTIVITY_ICONS['playing'], color='#B5BAC1', size=13)
        self._preview_dot = ft.Container(
            width=12, height=12, border_radius=6,
            bgcolor=_PRESENCE_COLORS[self._status_value],
            border=_border_all(2, '#232428'),
        )

        # Pull in whatever was saved from a previous session (if any).
        self._load_status_config()

    # ── translation shortcut ────────────────────────────────────────────────
    def _tt(self, key: str) -> str:
        return _t(key, self._lang)

    # ══════════════════════════════════════════════════════════════════════
    #  Persistence — status_config.json lives next to config.json inside
    #  bot_files (same resolution logic as _get_token in local_server.py),
    #  so the running bot can read it directly without going through the UI.
    # ══════════════════════════════════════════════════════════════════════

    def _status_config_path(self) -> str | None:
        if not self._bot_dir:
            return None
        abs_dir = os.path.abspath(self._bot_dir)
        if os.path.basename(abs_dir).lower() == 'bot_files':
            bot_root = os.path.dirname(abs_dir)
        else:
            bot_root = abs_dir
        return os.path.join(bot_root, 'bot_files', 'status_config.json')

    def _load_status_config(self):
        path = self._status_config_path()
        if not path or not os.path.isfile(path):
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return

        self._status_value    = data.get('status', self._status_value)
        self._loop_unit_value = data.get('loop_unit', self._loop_unit_value)
        loop_time = data.get('loop_time')
        if loop_time is not None:
            self._loop_time_field.value = str(loop_time)
        self._presence_checkbox.value = bool(data.get('enabled', False))

        entries = data.get('entries')
        if isinstance(entries, list):
            self._entries = entries

        self._preview_dot.bgcolor = _PRESENCE_COLORS.get(self._status_value, _PRESENCE_COLORS['online'])

    def _save_status_config(self):
        path = self._status_config_path()
        if not path:
            return

        raw_loop_time = (self._loop_time_field.value or '').strip()
        loop_time = int(raw_loop_time) if raw_loop_time.isdigit() else 30

        data = {
            'enabled':   bool(self._presence_checkbox.value),
            'status':    self._status_value,
            'loop_time': loop_time,
            'loop_unit': self._loop_unit_value,
            'entries':   self._entries,
        }

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _activity_label(self, key: str) -> str:
        return {
            'playing':   self._tt('sv_activity_playing'),
            'streaming': self._tt('sv_activity_streaming'),
            'listening': self._tt('sv_activity_listening'),
            'watching':  self._tt('sv_activity_watching'),
            'competing': self._tt('sv_activity_competing'),
        }[key]

    # ══════════════════════════════════════════════════════════════════════
    #  Screen 1 — Status Bot (list)
    # ══════════════════════════════════════════════════════════════════════

    def build(self) -> ft.Control:
        self._container = ft.Container(content=self._build_list_view(), expand=True)
        return self._container

    def _build_list_view(self) -> ft.Control:
        self._refresh_entries_col()

        body = ft.Column(
            [
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_color=self._c('text'),
                            on_click=lambda e: self._back_to_settings(),
                            style=ft.ButtonStyle(shape=ft.CircleBorder()),
                        ),
                        ft.Text(self._tt('status_bot_title'), size=20,
                                weight=ft.FontWeight.BOLD, color=self._c('text'), expand=True),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),

                # ── Status Bot card ─────────────────────────────────────────
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(self._tt('sv_status_label'), size=13,
                                            weight=ft.FontWeight.W_500,
                                            color=self._c('text'), expand=True),
                                    self._status_dropdown(),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Divider(color=self._c('divider'), height=1),
                            ft.Row(
                                [
                                    ft.Text(self._tt('sv_loop_time_label'), size=13,
                                            weight=ft.FontWeight.W_500,
                                            color=self._c('text'), expand=True),
                                ],
                            ),
                            ft.Row(
                                [
                                    self._loop_time_field,
                                    self._loop_unit_dropdown(),
                                ],
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.START,
                            ),
                            ft.Divider(color=self._c('divider'), height=1),
                            ft.Row(
                                [
                                    self._presence_checkbox,
                                    ft.IconButton(
                                        icon=ft.Icons.HELP_OUTLINE_ROUNDED,
                                        icon_color=self._c('text_dim'),
                                        icon_size=18,
                                        tooltip=self._tt('sv_help_note_title'),
                                        on_click=lambda e: self._show_help_note(),
                                        style=ft.ButtonStyle(shape=ft.CircleBorder()),
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=12,
                    ),
                    bgcolor=self._c('card_bg'),
                    border=_border_all(1, self._c('card_border')),
                    border_radius=14,
                    padding=ft.Padding(left=16, top=14, right=16, bottom=14),
                ),

                # ── Status entries card ─────────────────────────────────────
                ft.Column(
                    [
                        ft.Text(self._tt('sv_status_entries'), size=15,
                                weight=ft.FontWeight.BOLD, color=self._c('text')),
                        ft.Container(
                            content=ft.Column(
                                [
                                    self._add_entry_row(),
                                    ft.Divider(color=self._c('divider'), height=1),
                                    self._entries_col,
                                ],
                                spacing=10,
                            ),
                            bgcolor=self._c('card_bg'),
                            border=_border_all(1, self._c('card_border')),
                            border_radius=14,
                            padding=ft.Padding(left=14, top=14, right=14, bottom=14),
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=8),
            ],
            spacing=18,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        return ft.Container(content=body, padding=ft.Padding(16, 16, 16, 16), expand=True)

    def _status_dropdown(self) -> ft.Dropdown:
        return ft.Dropdown(
            value=self._status_value,
            width=170,
            dense=True,
            border_color=self._c('card_border'),
            focused_border_color=self._c('accent'),
            bgcolor=self._c('card_bg'),
            color=self._c('text'),
            text_style=ft.TextStyle(color=self._c('text'), size=13),
            options=[
                ft.DropdownOption(key=k, content=self._presence_option(k))
                for k in ('online', 'idle', 'dnd', 'invisible')
            ],
            on_select=self._on_status_select,
        )

    def _presence_option(self, key: str) -> ft.Control:
        labels = {
            'online':    self._tt('sv_status_online'),
            'idle':      self._tt('sv_status_idle'),
            'dnd':       self._tt('sv_status_dnd'),
            'invisible': self._tt('sv_status_invisible'),
        }
        return ft.Row(
            [
                ft.Container(width=10, height=10, border_radius=5,
                             bgcolor=_PRESENCE_COLORS[key]),
                ft.Text(labels[key], size=13, color=self._c('text')),
            ],
            spacing=8, tight=True,
        )

    def _on_status_select(self, e: ft.ControlEvent):
        self._status_value = e.control.value
        self._save_status_config()
        self._page.update()

    def _loop_unit_dropdown(self) -> ft.Dropdown:
        labels = {
            'second': self._tt('sv_unit_second'),
            'minute': self._tt('sv_unit_minute'),
            'hour':   self._tt('sv_unit_hour'),
            'day':    self._tt('sv_unit_day'),
        }
        return ft.Dropdown(
            value=self._loop_unit_value,
            width=120,
            dense=True,
            border_color=self._c('card_border'),
            focused_border_color=self._c('accent'),
            bgcolor=self._c('card_bg'),
            color=self._c('text'),
            text_style=ft.TextStyle(color=self._c('text'), size=13),
            options=[
                ft.DropdownOption(key=k, text=labels[k])
                for k in ('second', 'minute', 'hour', 'day')
            ],
            on_select=self._on_loop_unit_select,
        )

    def _on_loop_unit_select(self, e: ft.ControlEvent):
        self._loop_unit_value = e.control.value
        self._validate_loop_time()

    def _validate_loop_time(self):
        raw = (self._loop_time_field.value or '').strip()

        if raw == '':
            self._loop_time_field.error = None
        elif not raw.isdigit():
            # Anything that isn't a plain whole number — decimals, signs,
            # letters, etc. — is rejected outright.
            self._loop_time_field.error = self._tt('sv_loop_time_integer_error')
        else:
            value = int(raw)
            total_seconds = value * _LOOP_UNIT_SECONDS[self._loop_unit_value]
            if total_seconds < _LOOP_TIME_MIN_SECONDS:
                self._loop_time_field.error = self._tt('sv_loop_time_min_error')
            else:
                self._loop_time_field.error = None

        if self._loop_time_field.error is None and raw != '':
            self._save_status_config()

        if self._page:
            self._page.update()

    def _add_entry_row(self) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, color=self._c('accent'), size=20),
                    ft.Text(self._tt('sv_add_entry'), size=14,
                            weight=ft.FontWeight.W_500, color=self._c('accent'), expand=True),
                ],
                spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_click=lambda e: self._open_editor(index=None),
            border_radius=10,
            padding=ft.Padding(left=6, top=8, right=6, bottom=8),
            ink=True,
        )

    def _refresh_entries_col(self):
        self._entries_col.controls.clear()

        if not self._entries:
            self._entries_col.controls.append(
                ft.Text(self._tt('sv_no_entries'), size=12, color=self._c('text_dim'))
            )
            return

        for i, entry in enumerate(self._entries):
            self._entries_col.controls.append(self._entry_row(i, entry))

    def _entry_row(self, index: int, entry: dict) -> ft.Control:
        details = entry.get('details') or self._tt('sv_entry_details_ph')
        status  = entry.get('status') or ''
        activity_type = entry.get('activity_type')
        subtitle = f"{self._activity_label(activity_type)} ● {status}".strip() if activity_type and status else status

        return ft.Row(
            [
                ft.Text(str(index + 1), size=13, color=self._c('text_dim'), width=16),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(details, size=13, color=self._c('text'),
                                            weight=ft.FontWeight.W_500),
                                    ft.Text(subtitle, size=11, color=self._c('text_dim'))
                                    if subtitle else ft.Container(height=0),
                                ],
                                spacing=2, expand=True,
                            ),
                            ft.Icon(ft.Icons.DRAG_INDICATOR, color=self._c('text_dim'), size=18),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color=self._c('danger'),
                                icon_size=18,
                                on_click=lambda e, i=index: self._ask_delete_entry(i),
                                style=ft.ButtonStyle(shape=ft.CircleBorder()),
                            ),
                        ],
                        spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=self._c('input_bg'),
                    border=_border_all(1, self._c('input_border')),
                    border_radius=10,
                    padding=ft.Padding(left=12, top=8, right=6, bottom=8),
                    on_click=lambda e, i=index: self._open_editor(index=i),
                    ink=True,
                    expand=True,
                ),
            ],
            spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _show_help_note(self):
        def _close(_):
            self._page.pop_dialog()

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=self._c('card_bg'),
            shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, color=self._c('accent'), size=20),
                    ft.Text(self._tt('sv_help_note_title'), weight=ft.FontWeight.BOLD,
                            color=self._c('text'), size=15),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Text(self._tt('sv_help_note_body'), color=self._c('text_dim'), size=13),
                width=280,
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text(self._tt('ok') or 'OK', color=self._c('accent')),
                    on_click=_close,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.show_dialog(dlg)

    def _ask_delete_entry(self, index: int):
        if not (0 <= index < len(self._entries)):
            return
        name = (self._entries[index].get('details') or '').strip() or self._tt('sv_entry_details_ph')

        def _do(_):
            self._page.pop_dialog()
            self._delete_entry(index)

        def _cancel(_):
            self._page.pop_dialog()

        msg_template  = self._tt('delete_confirm') or 'Are you sure you want to delete "{item_name}"?\nThis action cannot be undone.'
        formatted_msg = msg_template.replace('{item_name}', name)

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=self._c('card_bg'),
            shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=self._c('danger'), size=22),
                    ft.Text(self._tt('delete_q') or 'Delete?', weight=ft.FontWeight.BOLD,
                            color=self._c('text'), size=16),
                ],
                spacing=8,
            ),
            content=ft.Text(formatted_msg, color=self._c('text_dim'), size=13),
            actions=[
                ft.TextButton(
                    content=ft.Text(self._tt('cancel') or 'Cancel', color=self._c('text_dim')),
                    on_click=_cancel,
                ),
                ft.FilledButton(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.DELETE_FOREVER_ROUNDED, color='#FFFFFF', size=16),
                         ft.Text(self._tt('delete') or 'Delete', color='#FFFFFF',
                                 weight=ft.FontWeight.BOLD)],
                        spacing=6, tight=True,
                    ),
                    on_click=_do,
                    style=ft.ButtonStyle(
                        bgcolor=self._c('danger'),
                        color='#FFFFFF',
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding(left=14, top=8, right=14, bottom=8),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.show_dialog(dlg)

    def _delete_entry(self, index: int):
        if 0 <= index < len(self._entries):
            self._entries.pop(index)
        self._save_status_config()
        self._refresh_entries_col()
        self._page.update()

    # ══════════════════════════════════════════════════════════════════════
    #  Screen 2 — Create / edit status entry
    # ══════════════════════════════════════════════════════════════════════

    def _open_editor(self, index: int | None):
        self._editing_index = index
        entry = self._entries[index] if index is not None else {}

        self._activity_type_value    = entry.get('activity_type', 'playing')
        self._activity_dropdown.value = self._activity_type_value
        self._edit_status_field.value = entry.get('status', '')
        self._stream_url_field.value  = entry.get('stream_url', '')
        self._stream_url_field.error  = None
        self._edit_details_field.value = entry.get('details', '')

        self._container.content = self._build_editor_view()
        self._page.update()
        self._refresh_preview()

    def _on_activity_select(self, e: ft.ControlEvent):
        self._activity_type_value     = e.control.value
        self._activity_dropdown.value = self._activity_type_value
        if self._activity_type_value != 'streaming':
            self._stream_url_field.error = None
        # Rebuild so the Stream URL field appears/disappears as needed.
        self._container.content = self._build_editor_view()
        self._page.update()
        self._refresh_preview()

    def _validate_stream_url(self):
        if self._activity_type_value != 'streaming':
            self._stream_url_field.error = None
        else:
            url = (self._stream_url_field.value or '').strip()
            if not url:
                self._stream_url_field.error = self._tt('sv_stream_url_required')
            elif not self._is_allowed_stream_url(url):
                self._stream_url_field.error = self._tt('sv_stream_url_invalid')
            else:
                self._stream_url_field.error = None
        self._refresh_preview()

    @staticmethod
    def _is_allowed_stream_url(url: str) -> bool:
        # Discord itself only renders the "Live" badge for Twitch and
        # YouTube links, so those are the only two hosts we accept.
        if not (url.startswith('http://') or url.startswith('https://')):
            return False
        try:
            host = urlparse(url).netloc.lower()
        except ValueError:
            return False
        host = host.split(':')[0]
        if host.startswith('www.'):
            host = host[4:]
        allowed_hosts = {'twitch.tv', 'youtube.com', 'youtu.be', 'm.youtube.com'}
        return host in allowed_hosts or any(
            host.endswith('.' + h) for h in allowed_hosts
        )

    def _build_editor_view(self) -> ft.Control:
        status_data_fields = [self._activity_dropdown, self._edit_status_field]
        if self._activity_type_value == 'streaming':
            status_data_fields.append(self._stream_url_field)
        status_data_fields.append(self._edit_details_field)

        body = ft.Column(
            [
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_color=self._c('text'),
                            on_click=lambda e: self._back_to_list(),
                            style=ft.ButtonStyle(shape=ft.CircleBorder()),
                        ),
                        ft.Text(self._tt('sv_create_edit_title'), size=17,
                                weight=ft.FontWeight.BOLD, color=self._c('text'), expand=True),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),

                # ── Status Data card ─────────────────────────────────────────
                ft.Column(
                    [
                        ft.Text(self._tt('sv_status_data'), size=15,
                                weight=ft.FontWeight.BOLD, color=self._c('text')),
                        ft.Container(
                            content=ft.Column(status_data_fields, spacing=18),
                            bgcolor=self._c('card_bg'),
                            border=_border_all(1, self._c('card_border')),
                            border_radius=14,
                            padding=ft.Padding(left=16, top=16, right=16, bottom=18),
                        ),
                    ],
                    spacing=8,
                ),

                ft.Column(
                    [
                        ft.Text(self._tt('sv_preview'), size=15,
                                weight=ft.FontWeight.BOLD, color=self._c('text')),
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Stack(
                                        [
                                            ft.Container(
                                                content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED,
                                                                 color='#FFFFFF', size=24),
                                                width=48, height=48, border_radius=24,
                                                bgcolor='#5865F2',
                                                alignment=ft.Alignment(0, 0),
                                            ),
                                            ft.Container(
                                                content=self._preview_dot,
                                                left=32, top=32,
                                            ),
                                        ],
                                        width=48, height=48,
                                    ),
                                    ft.Column(
                                        [
                                            ft.Row(
                                                [
                                                    self._preview_name_text,
                                                    ft.Container(
                                                        content=ft.Text(
                                                            self._tt('sv_app_badge'), size=9,
                                                            weight=ft.FontWeight.BOLD,
                                                            color='#FFFFFF',
                                                        ),
                                                        bgcolor='#5865F2',
                                                        border_radius=3,
                                                        padding=ft.Padding(left=4, right=4, top=1, bottom=1),
                                                    ),
                                                ],
                                                spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                            ),
                                            ft.Row(
                                                [
                                                    self._preview_activity_icon,
                                                    self._preview_status_text,
                                                ],
                                                spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                            ),
                                        ],
                                        spacing=4,
                                    ),
                                ],
                                spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            bgcolor='#313338',
                            border=_border_all(1, '#1E1F22'),
                            border_radius=8,
                            padding=ft.Padding(left=14, top=14, right=14, bottom=14),
                        ),
                    ],
                    spacing=8,
                ),

                ft.FilledButton(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.SAVE_OUTLINED, color='#FFFFFF', size=16),
                         ft.Text(self._tt('sv_save_entry'), color='#FFFFFF',
                                 weight=ft.FontWeight.BOLD)],
                        spacing=6, tight=True,
                    ),
                    on_click=lambda e: self._save_entry(),
                    style=_btn_style(self._c('success')),
                ),
                ft.Container(height=8),
            ],
            spacing=18,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        return ft.Container(content=body, padding=ft.Padding(16, 16, 16, 16), expand=True)

    def _refresh_preview(self):
        self._preview_name_text.value = self._tt('sv_name_bot')
        self._preview_dot.bgcolor     = _PRESENCE_COLORS[self._status_value]
        self._preview_activity_icon.icon = _ACTIVITY_ICONS[self._activity_type_value]

        verb   = self._activity_label(self._activity_type_value)
        status = (self._edit_status_field.value or '').strip()
        mark   = '●' if status else ''
        pieces = [p for p in (verb, mark, status) if p]
        text   = ' '.join(pieces)

        if self._activity_type_value == 'streaming' and (self._stream_url_field.value or '').strip():
            text += '  🔗'

        self._preview_status_text.value = text

        if self._page:
            self._page.update()

    def _save_entry(self):
        if self._activity_type_value == 'streaming':
            self._validate_stream_url()
            if self._stream_url_field.error:
                self._page.update()
                return

        entry = {
            'activity_type': self._activity_type_value,
            'status':      (self._edit_status_field.value or '').strip(),
            'stream_url':  (self._stream_url_field.value or '').strip()
                           if self._activity_type_value == 'streaming' else '',
            'details':     (self._edit_details_field.value or '').strip() or self._tt('sv_entry_details_ph'),
        }

        if self._editing_index is not None:
            self._entries[self._editing_index] = entry
        else:
            self._entries.append(entry)

        self._save_status_config()
        self._back_to_list()

    def _back_to_list(self):
        self._editing_index = None
        self._container.content = self._build_list_view()
        self._page.update()

    def _back_to_settings(self):
        if self._on_back:
            self._on_back()