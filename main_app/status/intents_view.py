# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/status/intents_view.py . Bot Intents (Developer Portal) page, Flet 0.85.2+ / v1 API

import asyncio
import base64
import json
import time

import flet as ft

_DISCORD_API  = 'https://discord.com/api/v10'
_INTENT_KEYS  = ('presence', 'members', 'content')
_INTENT_NAMES = {
    'presence': 'Presence Intent',
    'members':  'Server Members Intent',
    'content':  'Message Content Intent',
}

_INTENT_FLAGS = {
    'presence': (1 << 12) | (1 << 13),
    'members':  (1 << 14) | (1 << 15),
    'content':  (1 << 18) | (1 << 19),
}


def _bot_id_from_token(token: str) -> str:
    try:
        part = str(token or '').strip().split('.')[0]
        part += '=' * (-len(part) % 4)
        decoded = base64.b64decode(part).decode('utf-8')
        return decoded if decoded.isdigit() else ''
    except Exception:
        return ''


def _discord_request(path: str, token: str = '', timeout: float = 6.0):
    import ssl
    import urllib.request
    import urllib.error

    try:
        ctx = ssl.create_default_context()
    except Exception:
        ctx = ssl._create_unverified_context()

    headers = {'User-Agent': 'DiscordBot (https://github.com/obgwew/FDSB, v2.5.0)'}
    if token:
        headers['Authorization'] = f'Bot {token}'
    req = urllib.request.Request(f'{_DISCORD_API}{path}', headers=headers, method='GET')

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            status = resp.status
            body = resp.read().decode('utf-8')
    except urllib.error.HTTPError as he:
        return he.code, None, (time.perf_counter() - start) * 1000
    except Exception:
        return 0, None, (time.perf_counter() - start) * 1000

    elapsed = (time.perf_counter() - start) * 1000
    try:
        data = json.loads(body)
    except Exception:
        data = None
    return status, data, elapsed


def _read_bot_intents(token: str):
    status, data, _ms = _discord_request('/applications/@me', token)
    if status == 200 and isinstance(data, dict):
        flags = int(data.get('flags') or 0)
        result = {k: bool(flags & bits) for k, bits in _INTENT_FLAGS.items()}
        return True, result, str(data.get('id') or ''), ''
    if status in (401, 403):
        return False, {}, '', 'invalid_bot_token'
    return False, {}, '', 'intents_check_failed'


def _ping_discord():
    status, _data, ms = _discord_request('/gateway', timeout=5.0)
    return round(ms) if status == 200 else None


def _border_all(w: float, color: str) -> ft.Border:
    s = ft.BorderSide(w, color)
    return ft.Border(left=s, top=s, right=s, bottom=s)


class BotIntentsView:

    def __init__(self, page: ft.Page, theme_hex, t, bot_data: dict = None,
                 token_getter=None, on_back=None, is_bot_online=None,
                 notify=None, auto_check: bool = True):
        self._page          = page
        self._c             = theme_hex
        self._t             = t
        self._bot_data      = bot_data or {}
        self._token_getter  = token_getter
        self._on_back       = on_back
        self._is_bot_online = is_bot_online
        self._notify_cb     = notify
        self._auto_check    = auto_check
        self._auto_done     = False

        self._state     = {k: None for k in _INTENT_KEYS}
        self._app_id    = ''
        self._reach     = None
        self._ping_val  = ''
        self._ping_bad  = False
        self._busy      = False

        self._chips       = {}
        self._warn        = None
        self._portal_btn  = None
        self._check_btn   = None
        self._conn_dot    = None
        self._conn_text   = None
        self._ping_label  = None

    # ── helpers ─────────────────────────────────────────────────────────
    def _notify(self, message: str):
        if self._notify_cb:
            self._notify_cb(message, self._c('danger'))

    def _token(self) -> str:
        try:
            return (self._token_getter() if self._token_getter else '') or ''
        except Exception:
            return ''

    def _back(self, _=None):
        if self._on_back:
            self._on_back()

    def _card(self, content: ft.Control) -> ft.Container:
        return ft.Container(
            content=content,
            bgcolor=self._c('card_bg'),
            border=_border_all(1, self._c('card_border')),
            border_radius=14,
            padding=ft.Padding(left=16, top=14, right=16, bottom=14),
            shadow=ft.BoxShadow(
                spread_radius=0, blur_radius=16,
                color=ft.Colors.with_opacity(0.10, '#000000'),
                offset=ft.Offset(0, 6),
            ),
        )

    def _icon_chip(self, icon: str, size: int = 24) -> ft.Container:
        return ft.Container(
            content=ft.Icon(icon, size=15, color=self._c('accent')),
            width=size, height=size,
            border_radius=size * 0.34,
            bgcolor=self._c('bg'),
            alignment=ft.Alignment(0, 0),
        )

    def _chip_content(self, state) -> ft.Control:
        c, t = self._c, self._t
        if state == 'wait':
            icon, label, color = ft.Icons.HOURGLASS_EMPTY_ROUNDED, '...', c('text_dim')
        elif state is True:
            icon, label, color = ft.Icons.CHECK_ROUNDED, t('intent_on'), c('success')
        elif state is False:
            icon, label, color = ft.Icons.CLOSE_ROUNDED, t('intent_off'), c('danger')
        else:
            icon, label, color = ft.Icons.REMOVE_ROUNDED, t('intent_unchecked'), c('text_dim')
        return ft.Row(
            [ft.Icon(icon, size=13, color=color),
             ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color=color)],
            spacing=4, tight=True,
        )

    def _check_content(self) -> ft.Control:
        t = self._t
        if self._busy:
            label, icon = t('checking'), ft.Icons.HOURGLASS_EMPTY_ROUNDED
        elif any(v is not None for v in self._state.values()):
            label, icon = t('intents_recheck'), ft.Icons.REFRESH_ROUNDED
        else:
            label, icon = t('intents_check_btn'), ft.Icons.REFRESH_ROUNDED
        return ft.Row(
            [ft.Icon(icon, color='#FFFFFF', size=16),
             ft.Text(label, color='#FFFFFF', weight=ft.FontWeight.BOLD)],
            spacing=6, tight=True,
        )

    def _intent_row(self, key: str) -> ft.Control:
        c = self._c
        chip = ft.Container(
            content=self._chip_content(self._state[key]),
            bgcolor=c('bg'),
            border_radius=6,
            padding=ft.Padding(left=9, top=3, right=9, bottom=3),
        )
        self._chips[key] = chip
        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(_INTENT_NAMES[key], size=13,
                                    weight=ft.FontWeight.W_500, color=c('text')),
                            ft.Text(self._t(f'intent_{key}_sub'), size=11, color=c('text_dim')),
                        ],
                        spacing=1, expand=True,
                    ),
                    chip,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=0, top=8, right=0, bottom=8),
        )

    def _missing_text(self) -> str:
        names = ', '.join(_INTENT_NAMES[k] for k in _INTENT_KEYS if self._state[k] is False)
        return self._t('intents_missing_msg').replace('{missing}', names)

    def _paint_conn(self):
        if self._conn_text is None:
            return
        c = self._c
        online = None
        if self._is_bot_online is not None:
            try:
                online = bool(self._is_bot_online(self._bot_data))
            except Exception:
                online = None

        if online is not None:
            key, color = ('intents_bot_online', c('online')) if online else ('intents_bot_offline', c('offline'))
        elif self._reach is True:
            key, color = 'intents_discord_ok', c('online')
        elif self._reach is False:
            key, color = 'intents_discord_down', c('offline')
        else:
            key, color = 'intents_conn_unknown', c('text_dim')

        self._conn_dot.bgcolor = color
        self._conn_text.value = self._t(key)

    # ── build ───────────────────────────────────────────────────────────
    def build(self) -> ft.Control:
        c, t = self._c, self._t
        self._chips = {}
        missing = any(v is False for v in self._state.values())

        header = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK_ROUNDED,
                    icon_color=c('text'),
                    icon_size=22,
                    on_click=self._back,
                ),
                self._icon_chip(ft.Icons.VERIFIED_USER_OUTLINED),
                ft.Text(t('intents_section'), size=15, weight=ft.FontWeight.BOLD, color=c('text')),
            ],
            spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self._conn_dot  = ft.Container(width=9, height=9, border_radius=5)
        self._conn_text = ft.Text('', size=13, weight=ft.FontWeight.W_500, color=c('text'))
        self._paint_conn()

        rows = []
        for i, key in enumerate(_INTENT_KEYS):
            if i:
                rows.append(ft.Divider(color=c('divider'), height=1))
            rows.append(self._intent_row(key))

        self._warn = ft.Text(self._missing_text(), size=12, color=c('danger'), visible=missing)

        self._check_btn = ft.FilledButton(
            content=self._check_content(),
            on_click=lambda e: self._page.run_task(self._check_intents, e),
            disabled=self._busy,
            style=ft.ButtonStyle(bgcolor=c('accent'), color='#FFFFFF',
                                 shape=ft.RoundedRectangleBorder(radius=10)),
        )
        self._portal_btn = ft.OutlinedButton(
            content=ft.Row(
                [ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED, color=c('accent'), size=15),
                 ft.Text(t('open_dev_portal'), color=c('accent'), weight=ft.FontWeight.BOLD)],
                spacing=6, tight=True,
            ),
            visible=missing,
            on_click=lambda e: self._page.run_task(self._open_dev_portal, e),
            style=ft.ButtonStyle(side=ft.BorderSide(1, c('accent')),
                                 shape=ft.RoundedRectangleBorder(radius=10)),
        )

        self._ping_label = ft.Text(
            self._ping_val, size=11, weight=ft.FontWeight.BOLD,
            color=c('danger') if self._ping_bad else c('text_dim'),
        )
        ping_row = ft.Row(
            [
                ft.TextButton(
                    content=ft.Text(t('intents_ping_test'), size=11, color=c('text_dim')),
                    on_click=lambda e: self._page.run_task(self._ping_server, e),
                ),
                self._ping_label,
            ],
            spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        card = self._card(
            ft.Column(
                [
                    ft.Text(t('intents_desc'), size=12, color=c('text_dim')),
                    ft.Divider(color=c('divider'), height=1),
                    ft.Row(
                        [self._conn_dot, self._conn_text],
                        spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(rows, spacing=0),
                    self._warn,
                    ft.Row(
                        [self._check_btn, self._portal_btn],
                        spacing=8, wrap=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Divider(color=c('divider'), height=1),
                    ping_row,
                ],
                spacing=10,
            ),
        )

        root = ft.Column(
            [
                header,
                ft.Column(
                    [card, ft.Container(height=24)],
                    spacing=22, scroll=ft.ScrollMode.AUTO, expand=True,
                ),
            ],
            spacing=12, expand=True,
        )

        if self._auto_check and not self._auto_done:
            self._auto_done = True
            self._page.run_task(self._check_intents)
        return root

    def _refresh(self):
        if self._warn is None:
            return
        for key, chip in self._chips.items():
            chip.content = self._chip_content(self._state[key])
        missing = any(v is False for v in self._state.values())
        self._warn.value = self._missing_text()
        self._warn.visible = missing
        self._portal_btn.visible = missing
        self._check_btn.content = self._check_content()
        self._check_btn.disabled = self._busy
        self._ping_label.value = self._ping_val
        self._ping_label.color = self._c('danger') if self._ping_bad else self._c('text_dim')
        self._paint_conn()
        try:
            self._page.update()
        except Exception:
            pass

    # ── actions ─────────────────────────────────────────────────────────
    async def _check_intents(self, _=None):
        if self._busy:
            return
        token = self._token()
        if not token:
            self._notify(self._t('token_required'))
            return

        self._busy = True
        for k in _INTENT_KEYS:
            self._state[k] = 'wait'
        self._refresh()

        try:
            ok, result, app_id, err = await asyncio.to_thread(_read_bot_intents, token)
        except Exception as e:
            print(f'[Intents] check failed: {e}')
            ok, result, app_id, err = False, {}, '', 'intents_check_failed'

        if ok:
            for k in _INTENT_KEYS:
                self._state[k] = bool(result.get(k, False))
            self._app_id = app_id or self._app_id
            self._reach = True
        else:
            for k in _INTENT_KEYS:
                self._state[k] = None
            self._reach = (err == 'invalid_bot_token')
            self._notify(self._t(err))

        self._busy = False
        self._refresh()

    async def _ping_server(self, _=None):
        self._ping_val, self._ping_bad = '...', False
        self._refresh()
        try:
            ms = await asyncio.to_thread(_ping_discord)
        except Exception:
            ms = None
        if ms is None:
            self._ping_val, self._ping_bad, self._reach = self._t('intents_ping_none'), True, False
        else:
            self._ping_val, self._ping_bad, self._reach = f'{ms} ms', False, True
        self._refresh()

    async def _open_dev_portal(self, _=None):
        app_id = self._app_id or _bot_id_from_token(self._token())
        url = (
            f'https://discord.com/developers/applications/{app_id}/bot'
            if app_id else 'https://discord.com/developers/applications'
        )
        try:
            await self._page.launch_url(url)
        except Exception as e:
            print(f'[Intents] open portal failed: {e}')