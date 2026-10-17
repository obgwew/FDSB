# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/settings_bot.py . migrated to Flet 0.85.2+ / v1 API u
#
# Per-bot settings tab. Language, theme and storage helpers live in settings_app.py.

import os
import sys
import json
import time
import zipfile
import random
import shutil
import base64
import subprocess
import urllib.parse

import flet as ft

from main_app.status.status_view import BotStatusView
from main_app.status.intents_view import BotIntentsView
from main_app.load.token_vault import TokenVault

from main_app.settings_app import (
    is_mobile, get_persistent_base_dir, get_current_lang,
    _t, _c,
    _border_all, _soft_shadow, _card_container, _icon_chip,
)

def _humanize_saved_path(raw, file_name: str = '') -> str:
    if not raw:
        return ''
    raw = urllib.parse.unquote(str(raw).strip())

    if raw.startswith('file://'):
        raw = raw[len('file://'):]

    if raw.startswith('content://'):
        authority = raw[len('content://'):].split('/', 1)[0]
        tail = raw.rsplit('/document/', 1)[1] if '/document/' in raw else ''

        if tail.startswith('raw:'):
            raw = tail[4:]
        elif 'externalstorage' in authority and ':' in tail:
            volume, rel = tail.split(':', 1)
            if volume == 'primary':
                label = _t('internal_storage')
            elif volume == 'home':
                label = _t('documents_folder')
            else:
                label = f"{_t('sd_card')} ({volume})"
            return f'{label}/{rel}'.rstrip('/')
        elif 'downloads' in authority:
            return f"{_t('downloads_folder')}/{file_name}".rstrip('/')
        else:
            return raw

    for prefix in ('/storage/emulated/0', '/sdcard'):
        if raw.startswith(prefix):
            rest = raw[len(prefix):].lstrip('/')
            return f"{_t('internal_storage')}/{rest}".rstrip('/')
    return raw


_EXPORT_FOLDERS = ('bot_commands', 'bot_ids', 'bot_vars', 'guild_vars', 'user_vars')


def _collect_export_sources(base_dir: str, bot_name: str, bot_dir: str) -> dict:
    roots = [
        os.path.normpath(os.path.join(base_dir, 'app_data', bot_name)),
        os.path.normpath(bot_dir) if bot_dir else '',
    ]

    names = list(_EXPORT_FOLDERS)
    for root in roots:
        if root and os.path.isdir(root):
            for entry in sorted(os.listdir(root)):
                if (
                    'event' in entry.lower()
                    and entry not in names
                    and os.path.isdir(os.path.join(root, entry))
                ):
                    names.append(entry)

    sources = {}
    for folder in names:
        for root in roots:
            candidate = os.path.join(root, folder) if root else ''
            if candidate and os.path.isdir(candidate):
                sources[folder] = candidate
                break
    return sources


def _inspect_bot_token(token: str) -> tuple[bool, str]:
    if not token or not str(token).strip():
        return False, 'token_required'

    clean = str(token).strip().strip('"\'')
    if clean.lower().startswith('bot '):
        clean = clean[4:].strip()

    if clean.lower().startswith('mfa.'):
        return False, 'selfbot_token_blocked'

    parts = clean.split('.')
    if len(parts) != 3:
        return False, 'invalid_bot_token'

    try:
        p1 = parts[0]
        pad = 4 - len(p1) % 4
        if pad != 4:
            p1 += '=' * pad
        decoded_id = base64.b64decode(p1).decode('utf-8')
        if not decoded_id.isdigit() or len(decoded_id) < 17:
            return False, 'invalid_bot_token'
    except Exception:
        return False, 'invalid_bot_token'

    try:
        import urllib.request
        import urllib.error
        import ssl

        try:
            ssl_ctx = ssl.create_default_context()
        except Exception:
            ssl_ctx = ssl._create_unverified_context()

        bot_req = urllib.request.Request(
            "https://discord.com/api/v10/users/@me",
            headers={
                "Authorization": f"Bot {clean}",
                "User-Agent": "DiscordBot (https://github.com/obgwew, v1.0)",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(bot_req, timeout=5, context=ssl_ctx) as resp:
                if resp.status == 200:
                    user_data = json.loads(resp.read().decode('utf-8'))
                    if user_data.get("bot") is True:
                        return True, 'token_valid'
                    else:
                        return False, 'selfbot_token_blocked'
        except urllib.error.HTTPError as he:
            if he.code == 401:
                try:
                    user_req = urllib.request.Request(
                        "https://discord.com/api/v10/users/@me",
                        headers={
                            "Authorization": clean,
                            "User-Agent": "Mozilla/5.0",
                        },
                        method="GET",
                    )
                    with urllib.request.urlopen(user_req, timeout=4, context=ssl_ctx) as u_resp:
                        if u_resp.status == 200:
                            return False, 'selfbot_token_blocked'
                except Exception:
                    pass
                return False, 'invalid_bot_token'
    except Exception:
        pass

    return True, 'token_valid'


class BotSettingsTab:
    _current_view = property(
        lambda self: 'editor' if (self._status_view or self._intents_view) else 'list'
    )

    def __init__(self, page: ft.Page, bot_data: dict = None,
                 on_bot_save=None, on_theme_change=None, on_lang_change=None,   # on_theme_change / on_lang_change: unused, kept for compatibility (theme + language now live in settings_app.py)
                 is_bot_online=None):
        self._page              = page
        # Optional: callable(bot_data) -> bool telling whether the bot process is online.
        self._is_bot_online     = is_bot_online
        self._bot_data          = bot_data or {}
        self._on_bot_save       = on_bot_save
        self._loading_overlay: ft.Control | None = None

        self._container: ft.Container | None = None

        self._lang          = get_current_lang()

        self._export_file_picker = ft.FilePicker()
        try:
            self._clipboard = ft.Clipboard()
        except Exception:
            self._clipboard = None

        self._captcha_code = ''
        self._captcha_box_display = ft.Container(alignment=ft.Alignment(0, 0))
        self._captcha_field = ft.TextField(
            hint_text=_t('captcha_enter'),
            dense=True,
            max_length=3,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            border_color=_c('card_border'),
            focused_border_color=_c('danger'),
            cursor_color=_c('danger'),
            border_radius=10,
            width=220,
            text_style=ft.TextStyle(
                color=_c('text'),
                size=18,
                weight=ft.FontWeight.BOLD,
                letter_spacing=4,
            ),
            bgcolor=_c('input_bg'),
        )
        self._captcha_section = ft.Column([], spacing=12, visible=False)

        self._delete_init_btn = ft.FilledButton(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.DELETE_FOREVER, color='#FFFFFF', size=18),
                    ft.Text(_t('delete_bot_perm'), color='#FFFFFF', weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            on_click=self._show_captcha,
            style=ft.ButtonStyle(
                bgcolor=_c('danger'),
                color='#FFFFFF',
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding(left=22, top=14, right=22, bottom=14),
            ),
        )

        # Name / token fields: full card width everywhere; on phones they are
        # taller with larger text for touch.
        _mob = is_mobile()

        self._name_field = ft.TextField(
            label=_t('bot_name_hint'),
            dense=not _mob,
            prefix_icon=ft.Icons.SMART_TOY_OUTLINED,
            border_color=_c('card_border'),
            focused_border_color=_c('accent'),
            cursor_color=_c('accent'),
            border_radius=10,
            content_padding=ft.Padding(left=12, top=14, right=12, bottom=14),
            label_style=ft.TextStyle(color=_c('text_dim'), size=12),
            text_style=ft.TextStyle(color=_c('text'), size=14 if _mob else 13),
            bgcolor=_c('card_bg'),
        )
        self._token_field = ft.TextField(
            label=_t('bot_token_hint'),
            dense=not _mob,
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.VPN_KEY_OUTLINED,
            border_color=_c('card_border'),
            focused_border_color=_c('accent'),
            cursor_color=_c('accent'),
            border_radius=10,
            content_padding=ft.Padding(left=12, top=14, right=12, bottom=14),
            label_style=ft.TextStyle(color=_c('text_dim'), size=12),
            text_style=ft.TextStyle(color=_c('text'), size=14 if _mob else 13),
            bgcolor=_c('card_bg'),
        )

        self._root_col: ft.Column = None
        self._status_view: BotStatusView | None = None
        self._intents_view: BotIntentsView | None = None

    async def _open_link(self, url: str):
        await self._page.launch_url(url)

    def swipe_blocked(self) -> bool:
        return self._status_view is not None or self._intents_view is not None

    def handle_back(self) -> bool:
        if self._intents_view is not None:
            self._close_intents()
            return True
        if self._status_view is not None:
            self._close_status_bot()
            return True
        return False

    def _notify(self, message: str, color: str):
        try:
            snack = ft.SnackBar(
                content=ft.Text(message, color='#FFFFFF', weight=ft.FontWeight.W_500),
                bgcolor=color,
                behavior=ft.SnackBarBehavior.FLOATING,
                shape=ft.RoundedRectangleBorder(radius=10),
            )
            if hasattr(self._page, 'show_dialog'):
                self._page.show_dialog(snack)
            elif hasattr(self._page, 'open'):
                self._page.open(snack)
            else:
                self._page.snack_bar = snack
                snack.open = True
                self._page.update()
        except Exception:
            pass

    def build(self) -> ft.Control:
        _added = False
        for _svc in (self._export_file_picker, self._clipboard):
            if _svc is not None and _svc not in self._page.services:
                self._page.services.append(_svc)
                _added = True
        if _added:
            self._page.update()

        self._root_col = ft.Column(
            [
                ft.Column(
                    [
                        self._build_general_section(),
                        self._build_status_bot_section(),
                        self._build_export_section(),
                        self._build_intents_section(),
                        self._build_info_section(),
                        self._build_delete_section(),
                        ft.Container(height=24),
                    ],
                    spacing=22,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
            ],
            expand=True,
        )

        self._container = ft.Container(
            content=self._root_col,
            padding=ft.Padding(left=16, top=16, right=16, bottom=0),
            expand=True,
        )
        return self._container

    def _rebuild_in_place(self):
        if self._root_col is None:
            return
        inner = self._root_col.controls[0]
        inner.controls = [
            self._build_general_section(),
            self._build_status_bot_section(),
            self._build_export_section(),
            self._build_intents_section(),
            self._build_info_section(),
            self._build_delete_section(),
            ft.Container(height=24),
        ]
        self._page.update()

    def _build_general_section(self) -> ft.Control:
        return ft.Column(
            [
                self._section_title(_t('general_section'), ft.Icons.TUNE_ROUNDED),
                _card_container(
                    ft.Column(
                        [
                            self._name_field,
                            self._token_field,
                            ft.Row(
                                [
                                    ft.FilledButton(
                                        content=ft.Row(
                                            [
                                                ft.Icon(ft.Icons.SAVE_OUTLINED, color='#FFFFFF', size=16),
                                                ft.Text(_t('save'), color='#FFFFFF', weight=ft.FontWeight.BOLD),
                                            ],
                                            spacing=6,
                                            tight=True,
                                        ),
                                        on_click=lambda e: self._page.run_task(self._save_bot, e),
                                        style=ft.ButtonStyle(
                                            bgcolor=_c('success'),
                                            color='#FFFFFF',
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                            padding=ft.Padding(left=14, top=10, right=14, bottom=10),
                                        ),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.START,
                            ),
                        ],
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                ),
            ],
            spacing=8,
        )

    def _show_loading(self, message: str = ''):
        if self._loading_overlay is not None:
            return
        message = message or _t('applying_changes')
        self._loading_overlay = ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(color=_c('accent'), width=36, height=36, stroke_width=3),
                    ft.Text(message, color=_c('text_dim'), size=12),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
            ),
            bgcolor=_c('bg') + 'EE',
            expand=True,
            alignment=ft.Alignment(0, 0),
        )
        try:
            self._page.overlay.append(self._loading_overlay)
            self._page.update()
        except Exception as e:
            print(f'[Settings] _show_loading failed: {e}')
            self._loading_overlay = None

    def hide_loading(self):
        if self._loading_overlay is None:
            return
        try:
            if self._loading_overlay in self._page.overlay:
                self._page.overlay.remove(self._loading_overlay)
            self._page.update()
        except Exception as e:
            print(f'[Settings] hide_loading failed: {e}')
        finally:
            self._loading_overlay = None

    def _show_export_notice_dialog(self, _):
        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=_c('card_bg'),
            shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row(
                [
                    _icon_chip(ft.Icons.INFO_OUTLINE_ROUNDED, bgcolor=_c('bg'), icon_color=_c('accent'), size=26),
                    ft.Text(_t('export_notice_title'), weight=ft.FontWeight.BOLD, size=15, color=_c('text')),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Text(
                _t('export_notice_desc'),
                color=_c('text_dim'),
                size=13,
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text(_t('ok'), color=_c('accent'), weight=ft.FontWeight.BOLD),
                    on_click=lambda _: self._page.pop_dialog(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.show_dialog(dlg)

    def _build_export_section(self) -> ft.Control:
        return ft.Column(
            [
                self._section_title(_t('export_section'), ft.Icons.ARCHIVE_OUTLINED),
                _card_container(
                    ft.Column(
                        [
                            ft.Text(
                                _t('export_desc'),
                                size=12, color=_c('text_dim'),
                            ),
                            ft.Divider(color=_c('divider'), height=1),
                            ft.Row(
                                [
                                    ft.FilledButton(
                                        content=ft.Row(
                                            [ft.Icon(ft.Icons.ARCHIVE_OUTLINED, color='#FFFFFF', size=16),
                                             ft.Text(_t('export_zip'),
                                                     color='#FFFFFF', weight=ft.FontWeight.BOLD)],
                                            spacing=6, tight=True,
                                        ),
                                        on_click=lambda e: self._page.run_task(self._export_bot_data, e),
                                        style=ft.ButtonStyle(bgcolor=_c('accent'), color='#FFFFFF', shape=ft.RoundedRectangleBorder(radius=10)),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.HELP_OUTLINE_ROUNDED,
                                        icon_color=_c('text_dim'),
                                        icon_size=20,
                                        tooltip=_t('export_notice_title'),
                                        on_click=self._show_export_notice_dialog,
                                    ),
                                ],
                                spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=10,
                    ),
                ),
            ],
            spacing=8,
        )

    def _build_intents_section(self) -> ft.Control:
        return ft.Column(
            [
                self._section_title(_t('intents_section'), ft.Icons.VERIFIED_USER_OUTLINED),
                _card_container(
                    ft.Column(
                        [
                            ft.Text(
                                _t('intents_entry_desc'),
                                size=12, color=_c('text_dim'),
                            ),
                            ft.Divider(color=_c('divider'), height=1),
                            ft.FilledButton(
                                content=ft.Row(
                                    [ft.Icon(ft.Icons.VERIFIED_USER_OUTLINED, color='#FFFFFF', size=16),
                                     ft.Text(_t('intents_open_btn'),
                                             color='#FFFFFF', weight=ft.FontWeight.BOLD)],
                                    spacing=6, tight=True,
                                ),
                                on_click=self._open_intents,
                                style=ft.ButtonStyle(bgcolor=_c('accent'), color='#FFFFFF',
                                                      shape=ft.RoundedRectangleBorder(radius=10)),
                            ),
                        ],
                        spacing=10,
                    ),
                ),
            ],
            spacing=8,
        )

    def _resolve_token(self) -> str:
        raw = (
            self._token_field.value
            or self._bot_data.get('token')
            or TokenVault.get_cached_for_dir(self._bot_data.get('bot_dir', ''))
            or ''
        )
        clean = str(raw).strip().strip('"\'')
        if clean.lower().startswith('bot '):
            clean = clean[4:].strip()
        return clean

    def _open_intents(self, _):
        if self._intents_view is None:
            self._intents_view = BotIntentsView(
                self._page, theme_hex=_c, t=_t, bot_data=self._bot_data,
                token_getter=self._resolve_token, on_back=self._close_intents,
                is_bot_online=self._is_bot_online, notify=self._notify,
            )
        self._container.content = self._intents_view.build()
        self._page.update()

    def _close_intents(self, _=None):
        self._intents_view = None
        self._container.content = self._root_col
        self._page.update()

    def _build_status_bot_section(self) -> ft.Control:
        return ft.Column(
            [
                self._section_title(_t('status_bot_section'), ft.Icons.BUBBLE_CHART_OUTLINED),
                _card_container(
                    ft.Column(
                        [
                            ft.Text(
                                _t('status_bot_desc'),
                                size=12, color=_c('text_dim'),
                            ),
                            ft.Divider(color=_c('divider'), height=1),
                            ft.FilledButton(
                                content=ft.Row(
                                    [ft.Icon(ft.Icons.BUBBLE_CHART_OUTLINED, color='#FFFFFF', size=16),
                                     ft.Text(_t('open_status_bot'),
                                             color='#FFFFFF', weight=ft.FontWeight.BOLD)],
                                    spacing=6, tight=True,
                                ),
                                on_click=self._open_status_bot,
                                style=ft.ButtonStyle(bgcolor=_c('accent'), color='#FFFFFF',
                                                      shape=ft.RoundedRectangleBorder(radius=10)),
                            ),
                        ],
                        spacing=10,
                    ),
                ),
            ],
            spacing=8,
        )

    def _open_status_bot(self, _):
        if self._status_view is None:
            self._status_view = BotStatusView(
                self._page, theme_hex=_c, bot_data=self._bot_data,
                lang=self._lang, on_back=self._close_status_bot,
            )
        self._container.content = self._status_view.build()
        self._page.update()

    def _close_status_bot(self, _=None):
        self._status_view = None
        self._container.content = self._root_col
        self._page.update()

    def _build_info_section(self) -> ft.Control:
        rows = [
            ('github',  'https://github.com/obgwew/FDSB'),
            ('discord', 'https://discord.gg/JngaJRC6Y9'),
        ]
        return ft.Column(
            [
                self._section_title(_t('info_section'), ft.Icons.INFO_OUTLINE_ROUNDED),
                _card_container(
                    ft.Column(
                        [self._info_row(lk, url) for lk, url in rows],
                        spacing=8,
                    ),
                ),
            ],
            spacing=8,
        )

    def _generate_noise_captcha_content(self) -> ft.Control:
        noise_layers = []

        # 1. Random noise dots distributed inside the box
        for _ in range(32):
            left_pos = random.randint(6, 240)
            top_pos  = random.randint(6, 60)
            dsize    = random.choice([2, 3, 4])
            dopacity = random.uniform(0.18, 0.40)
            noise_layers.append(
                ft.Container(
                    left=left_pos,
                    top=top_pos,
                    width=dsize,
                    height=dsize,
                    border_radius=dsize // 2,
                    bgcolor=ft.Colors.with_opacity(dopacity, _c('danger')),
                )
            )

        # 2. Random scratch noise lines
        for _ in range(4):
            l_x = random.randint(5, 70)
            l_y = random.randint(12, 54)
            l_w = random.randint(90, 180)
            l_rot = random.uniform(-0.25, 0.25)
            noise_layers.append(
                ft.Container(
                    left=l_x,
                    top=l_y,
                    width=l_w,
                    height=1.5,
                    rotate=ft.Rotate(angle=l_rot),
                    bgcolor=ft.Colors.with_opacity(random.uniform(0.20, 0.35), _c('text')),
                )
            )

        # 3. Digits - large, bold, and clearly visible
        digit_items = []
        palette = [_c('text'), _c('danger'), _c('accent'), '#D97706']
        for ch in self._captcha_code:
            rot = random.uniform(-0.18, 0.18)
            f_size = random.randint(34, 38)
            color = random.choice(palette)
            digit_items.append(
                ft.Container(
                    content=ft.Text(
                        ch,
                        size=f_size,
                        weight=ft.FontWeight.W_900,
                        color=color,
                        selectable=False,
                        font_family="monospace",
                    ),
                    rotate=ft.Rotate(angle=rot),
                    padding=ft.Padding(left=8, right=8, top=0, bottom=0),
                )
            )

        digits_row = ft.Container(
            content=ft.Row(
                digit_items,
                spacing=16,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )
        noise_layers.append(digits_row)

        # 4. Foreground cross-cutting line
        noise_layers.append(
            ft.Container(
                left=15,
                top=34,
                width=220,
                height=2,
                rotate=ft.Rotate(angle=random.uniform(-0.10, 0.10)),
                bgcolor=ft.Colors.with_opacity(0.35, _c('danger')),
            )
        )

        return ft.Stack(
            controls=noise_layers,
            width=250,
            height=70,
        )

    def _regenerate_captcha(self):
        self._captcha_code = ''.join(random.choices('0123456789', k=3))
        self._captcha_box_display.content = self._generate_noise_captcha_content()

    def _build_delete_section(self) -> ft.Control:
        self._regenerate_captcha()

        captcha_refresh_row = ft.Row(
            [
                ft.Container(
                    content=self._captcha_box_display,
                    bgcolor=_c('card_bg'),
                    border=_border_all(2, _c('danger')),
                    border_radius=8,
                    padding=ft.Padding(left=12, top=6, right=12, bottom=6),
                    alignment=ft.Alignment(0, 0),
                ),
                ft.IconButton(
                    icon=ft.Icons.REFRESH_ROUNDED,
                    icon_color=_c('text_dim'),
                    tooltip=_t('refresh_code'),
                    on_click=lambda _: (self._regenerate_captcha(), self._page.update()),
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self._captcha_section = ft.Column(
            [
                captcha_refresh_row,
                ft.Text(
                    _t('captcha_hint'),
                    size=12,
                    color=_c('text_dim'),
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Row(
                    [self._captcha_field],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ft.TextButton(
                            content=ft.Text(_t('cancel'), color=_c('text_dim'), weight=ft.FontWeight.W_500),
                            on_click=self._hide_captcha,
                        ),
                        ft.FilledButton(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.WARNING_ROUNDED, color='#FFFFFF', size=18),
                                    ft.Text(_t('confirm_delete'), color='#FFFFFF', weight=ft.FontWeight.BOLD),
                                ],
                                spacing=6,
                                tight=True,
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            on_click=self._execute_deletion,
                            style=ft.ButtonStyle(
                                bgcolor='#991B1B',
                                color='#FFFFFF',
                                shape=ft.RoundedRectangleBorder(radius=10),
                                padding=ft.Padding(left=18, top=12, right=18, bottom=12),
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            visible=False,
        )

        delete_init_row = ft.Row(
            [self._delete_init_btn],
            alignment=ft.MainAxisAlignment.CENTER,
        )

        return ft.Column(
            [
                ft.Row(
                    [
                        _icon_chip(ft.Icons.WARNING_AMBER_ROUNDED, bgcolor=_c('bg'),
                                   icon_color=_c('danger'), size=24),
                        ft.Text(_t('danger_zone'), size=13, weight=ft.FontWeight.BOLD,
                                color=_c('danger')),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            delete_init_row,
                            self._captcha_section,
                        ],
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=_c('card_bg'),
                    border=_border_all(1, _c('danger')),
                    border_radius=14,
                    padding=ft.Padding(left=16, top=14, right=16, bottom=14),
                    shadow=_soft_shadow(opacity=0.06),
                ),
            ],
            spacing=8,
        )

    def _section_title(self, text: str, icon: str = None) -> ft.Control:
        if not icon:
            return ft.Text(text, size=12, weight=ft.FontWeight.BOLD, color=_c('text_dim'))
        return ft.Row(
            [
                _icon_chip(icon, bgcolor=_c('bg'), icon_color=_c('accent'), size=24),
                ft.Text(text, size=13, weight=ft.FontWeight.BOLD, color=_c('text')),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _info_row(self, label_key: str, url: str) -> ft.Control:
        icons = {'github': ft.Icons.CODE_ROUNDED,
                 'discord': ft.Icons.TAG}

        colors = {'github': _c('accent'),
                  'discord': '#5865F2'}

        return ft.Container(
            content=ft.Row(
                [
                    _icon_chip(icons.get(label_key, ft.Icons.LINK),
                               bgcolor=_c('bg'),
                               icon_color=colors.get(label_key, _c('accent')), size=32),
                    ft.Text(_t(label_key), size=13, color=_c('text'),
                            weight=ft.FontWeight.W_500, expand=True),
                    ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED, color=_c('text_dim'), size=16),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=52,
            border_radius=10,
            padding=ft.Padding(left=6, right=10, top=0, bottom=0),
            ink=True,
            on_click=lambda _, u=url: self._page.run_task(self._open_link, u),
        )

    async def _copy_text(self, text: str) -> bool:
        try:
            if self._clipboard is not None:
                await self._clipboard.set(text)
                return True
        except Exception as e:
            print(f'[Settings] clipboard failed: {e}')
        try:
            self._page.set_clipboard(text)
            return True
        except Exception:
            return False

    def _show_export_result_dialog(self, location: str, file_name: str, exact: bool = True):
        """Tell the user where the exported ZIP ended up."""
        async def _on_copy(_):
            if await self._copy_text(location):
                self._notify(_t('path_copied'), _c('success'))

        body = [
            ft.Text(_t('export_saved_to') if exact else _t('export_path_unknown'),
                    color=_c('text_dim'), size=13),
        ]
        if exact:
            body.append(
                ft.Container(
                    content=ft.Text(location, selectable=True, size=13,
                                    color=_c('text'), weight=ft.FontWeight.W_500),
                    padding=ft.Padding.all(10),
                    border_radius=10,
                    bgcolor=_c('bg'),
                )
            )
        body.append(
            ft.Text(f"{_t('export_file_name')}: {file_name}",
                    color=_c('text_dim'), size=12, selectable=True)
        )

        actions = []
        if exact:
            actions.append(
                ft.TextButton(
                    content=ft.Text(_t('copy_path'), color=_c('text_dim')),
                    on_click=_on_copy,
                )
            )
        actions.append(
            ft.TextButton(
                content=ft.Text(_t('ok'), color=_c('accent'), weight=ft.FontWeight.BOLD),
                on_click=lambda _: self._page.pop_dialog(),
            )
        )

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=_c('card_bg'),
            shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row(
                [
                    _icon_chip(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                               bgcolor=_c('bg'), icon_color=_c('success'), size=26),
                    ft.Text(_t('export_saved_title'), weight=ft.FontWeight.BOLD,
                            size=15, color=_c('text')),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Column(body, spacing=10, tight=True),
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.show_dialog(dlg)

    def _show_mobile_export_dialog(self, zip_name: str, zip_path: str):
        """Mobile: the user taps a button to pick the save location through the
        system picker, then the chosen location is shown."""
        title_txt = ft.Text(_t('export_ready_title'), weight=ft.FontWeight.BOLD,
                            size=15, color=_c('text'))
        desc_txt  = ft.Text(_t('export_ready_desc'), color=_c('text_dim'), size=13)
        name_txt  = ft.Text(f"{_t('export_file_name')}: {zip_name}",
                            color=_c('text_dim'), size=12, selectable=True)
        path_txt  = ft.Text('', selectable=True, size=13,
                            color=_c('text'), weight=ft.FontWeight.W_500)
        path_box  = ft.Container(content=path_txt, padding=ft.Padding.all(10),
                                 border_radius=10, bgcolor=_c('bg'), visible=False)
        btn_label = ft.Text(_t('choose_location'), color='#FFFFFF', weight=ft.FontWeight.BOLD)
        copy_btn  = ft.TextButton(content=ft.Text(_t('copy_path'), color=_c('text_dim')),
                                  visible=False)
        close_lbl = ft.Text(_t('cancel'), color=_c('text_dim'), weight=ft.FontWeight.BOLD)
        busy = {'v': False}

        async def _on_copy(_):
            if await self._copy_text(path_txt.value):
                self._notify(_t('path_copied'), _c('success'))
        copy_btn.on_click = _on_copy

        async def _on_choose(_):
            if busy['v']:
                return
            busy['v'] = True
            try:
                with open(zip_path, 'rb') as f:
                    zip_bytes = f.read()
                saved = await self._export_file_picker.save_file(
                    dialog_title=_t('export_zip'),
                    file_name=zip_name,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=['zip'],
                    src_bytes=zip_bytes,
                )
            except Exception as e:
                print(f'[Settings] save failed: {e}')
                self._notify(_t('export_failed'), _c('danger'))
                return
            finally:
                busy['v'] = False

            if not saved:      # user cancelled the system picker; stay here
                return

            location = _humanize_saved_path(saved, zip_name)
            exact = bool(location) and location != zip_name
            title_txt.value = _t('export_saved_title')
            desc_txt.value  = _t('export_saved_to') if exact else _t('export_path_unknown')
            path_txt.value  = location
            path_box.visible = exact
            copy_btn.visible = exact
            btn_label.value  = _t('choose_other_location')
            close_lbl.value  = _t('ok')
            close_lbl.color  = _c('accent')
            self._page.update()

        choose_btn = ft.FilledButton(
            content=ft.Row(
                [ft.Icon(ft.Icons.FOLDER_OPEN_ROUNDED, color='#FFFFFF', size=18), btn_label],
                spacing=8, tight=True, alignment=ft.MainAxisAlignment.CENTER,
            ),
            on_click=_on_choose,
            style=ft.ButtonStyle(bgcolor=_c('accent'), color='#FFFFFF',
                                 shape=ft.RoundedRectangleBorder(radius=10)),
        )

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=_c('card_bg'),
            shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row(
                [_icon_chip(ft.Icons.ARCHIVE_OUTLINED, bgcolor=_c('bg'),
                            icon_color=_c('accent'), size=26), title_txt],
                spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Column([desc_txt, name_txt, choose_btn, path_box],
                              spacing=12, tight=True),
            actions=[
                copy_btn,
                ft.TextButton(content=close_lbl, on_click=lambda _: self._page.pop_dialog()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.show_dialog(dlg)

    async def _export_bot_data(self, _):
        bot_name = self._bot_data.get('name', '').strip()
        bot_dir  = self._bot_data.get('bot_dir', '').strip()

        if not bot_name or not bot_dir:
            self._notify(_t('no_bot_selected'), _c('danger'))
            return

        base_dir   = get_persistent_base_dir()
        export_dir = os.path.normpath(os.path.join(base_dir, 'app_data', 'exports'))
        os.makedirs(export_dir, exist_ok=True)

        zip_name = f'{bot_name}_export.zip'
        zip_path = os.path.join(export_dir, zip_name)

        sources = _collect_export_sources(base_dir, bot_name, bot_dir)

        if not sources:
            self._notify(_t('folders_not_found'), _c('danger'))
            return

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for folder_name, folder_path in sources.items():
                    for root, _dirs, files in os.walk(folder_path):
                        for file in files:
                            abs_p = os.path.join(root, file)
                            arc   = os.path.join(
                                folder_name, os.path.relpath(abs_p, folder_path)
                            )
                            zf.write(abs_p, arc)
        except Exception as e:
            print(f'[Settings] Export failed: {e}')
            self._notify(_t('export_failed'), _c('danger'))
            return

        try:
            if is_mobile():
                self._show_mobile_export_dialog(zip_name, zip_path)
                return
            else:
                if sys.platform == 'win32':
                    subprocess.Popen(['explorer', '/select,', zip_path])
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', '-R', zip_path])
                else:
                    subprocess.Popen(['xdg-open', export_dir])
                self._show_export_result_dialog(zip_path, zip_name, True)
                return
        except Exception as e:
            print(f'[Settings] reveal/save failed: {e}')
            self._notify(_t('export_failed'), _c('danger'))
            return

        self._notify(_t('export_success'), _c('success'))

    def _show_captcha(self, _):
        self._regenerate_captcha()
        self._captcha_field.value      = ''
        self._captcha_field.error_text = None
        self._captcha_section.visible  = True
        self._delete_init_btn.visible  = False
        self._page.update()

    def _hide_captcha(self, _=None):
        self._captcha_field.value      = ''
        self._captcha_field.error_text = None
        self._captcha_section.visible  = False
        self._delete_init_btn.visible  = True
        self._page.update()

    def _execute_deletion(self, _):
        if (self._captcha_field.value or '').strip() != self._captcha_code:
            self._regenerate_captcha()
            self._captcha_field.value      = ''
            self._captcha_field.error_text = _t('captcha_wrong')
            self._page.update()
            return

        base_dir = get_persistent_base_dir()
        bot_name = self._bot_data.get('name', '')
        _bot_dir = self._bot_data.get('bot_dir', '')

        # Remove token from vault
        if _bot_dir:
            _bot_id = TokenVault.bot_id_from_dir(_bot_dir)
            TokenVault.forget_cached(_bot_id)
            try:
                self._page.run_task(TokenVault.remove, _bot_id)
            except Exception as e:
                print(f'[Settings] token remove failed: {e}')

        # Remove app_data folder for this bot
        if bot_name:
            target = os.path.normpath(os.path.join(base_dir, 'app_data', bot_name))
            if os.path.exists(target):
                try:
                    shutil.rmtree(target)
                    print(f'[Settings] Deleted app_data target: {target}')
                except Exception as e:
                    print(f'[Settings] Delete failed: {e}')

        # Remove bot_dir if separate
        if _bot_dir and os.path.exists(_bot_dir) and _bot_dir != base_dir:
            try:
                shutil.rmtree(_bot_dir)
                print(f'[Settings] Deleted bot directory: {_bot_dir}')
            except Exception as e:
                print(f'[Settings] Delete bot_dir failed: {e}')

        # Reset bot state cleanly
        self._bot_data = {}
        self._name_field.value = ''
        self._token_field.value = ''
        self._hide_captcha()

        # Trigger main FDSB interface callback to seamlessly navigate back to dashboard/bot creation
        if self._on_bot_save:
            self._on_bot_save({})

        self._page.update()

    async def _save_bot(self, _):
        new_name  = (self._name_field.value or '').strip()
        new_token = (self._token_field.value or '').strip()

        if not new_token:
            self._token_field.error_text = _t('token_required')
            self._notify(_t('token_required'), _c('danger'))
            self._page.update()
            return

        old_token = (
            self._bot_data.get('token')
            or TokenVault.get_cached_for_dir(self._bot_data.get('bot_dir', ''))
            or ''
        ).strip()
        if new_token != old_token:
            is_valid, reason = _inspect_bot_token(new_token)
            if not is_valid:
                err_msg = _t(reason)
                self._token_field.error_text = err_msg
                self._notify(err_msg, _c('danger'))
                self._page.update()
                return

        self._token_field.error_text = None
        bot_dir = self._bot_data.get('bot_dir', '')

        if bot_dir:
            config_path = os.path.join(bot_dir, 'bot_files', 'config.json')
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                cfg['name'] = new_name or cfg.get('name', 'Bot')
                cfg.pop('token', None)
                cfg['token_storage'] = 'secure'
                if new_token != old_token:
                    await TokenVault.set(TokenVault.bot_id_from_dir(bot_dir), new_token)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                self._bot_data.update({'name': cfg['name'], 'token': new_token})
            except Exception as e:
                print(f'[Settings] save failed: {e}')
                self._notify(_t('save_error').format(error=e), _c('danger'))
                self._page.update()
                return

        if self._on_bot_save:
            self._on_bot_save(self._bot_data)

        self._notify(_t('saved_successfully'), _c('success'))
        self._page.update()

    def load_bot(self, bot_data: dict):
        self._bot_data          = bot_data
        self._name_field.value  = bot_data.get('name',  '')
        self._token_field.value = (
            bot_data.get('token')
            or TokenVault.get_cached_for_dir(bot_data.get('bot_dir', ''))
            or ''
        )
        self._hide_captcha()