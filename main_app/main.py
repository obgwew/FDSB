# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/main.py . migrated to Flet 0.85.2+ / v1 API 

import os
import json
import base64
import shutil
import threading
import time

import flet as ft

from main_app.settings import BotSettingsTab, get_current_lang, is_mobile
from main_app.load.token_vault import TokenVault
from main_app.commands_view import BotCommandsTab
from main_app.langs.translations import Translations
from main_app.theme.theme_engine import ThemeEngine
from main_app.variables_view import BotVariablesTab
from main_app.wiki_view import BotWikiTab
from main_app.load.motion import SlideStack, SwipeController

NEW_TXT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'main_app/new.txt'
)

_AVATAR_EXTS = ('.png', '.jpg', '.jpeg', '.webp', '.gif')


def _t(key: str) -> str:
    return Translations.get(key, get_current_lang())


# last error raised while importing main_app.core_fdsb (shown to the user instead of failing silently)
_CORE_ERR = {'msg': ''}

def _run_bg(page: ft.Page, fn, *args):
    runner = getattr(page, 'run_thread', None)
    if callable(runner):
        try:
            runner(fn, *args)
            return
        except Exception:
            pass
    threading.Thread(target=fn, args=args, daemon=True).start()


def _c(key: str) -> str:
    return ThemeEngine.hex(key)


def _theme_unsub(cb):
    """Remove a ThemeEngine subscription (works even without ThemeEngine.unsubscribe)."""
    fn = getattr(ThemeEngine, 'unsubscribe', None)
    if callable(fn):
        try:
            fn(cb)
            return
        except Exception:
            pass
    for holder in (ThemeEngine, getattr(ThemeEngine, '_instance', None)):
        if holder is None:
            continue
        for val in list(vars(holder).values()):
            try:
                if isinstance(val, list) and cb in val:
                    val.remove(cb)
                elif isinstance(val, set) and cb in val:
                    val.discard(cb)
            except Exception:
                pass


def _get_bot_id_from_token(token: str) -> str:
    try:
        clean_token = token.strip().strip('"\'')
        if clean_token.lower().startswith('bot '):
            clean_token = clean_token[4:].strip()
        part1 = clean_token.split('.')[0]
        padding = 4 - len(part1) % 4
        if padding != 4:
            part1 += '=' * padding
        return base64.b64decode(part1).decode('utf-8')
    except Exception:
        return ''


def _validate_discord_token(token: str) -> bool:
    if not token or not str(token).strip():
        return False

    clean_token = str(token).strip().strip('"\'')
    if clean_token.lower().startswith("bot "):
        clean_token = clean_token[4:].strip()

    if not clean_token:
        return False

    url = "https://discord.com/api/v10/users/@me"
    headers = {
        "Authorization": f"Bot {clean_token}",
        "User-Agent": "DiscordBot (https://github.com/obgwew, v1.0)",
    }

    try:
        import urllib.request
        import urllib.error
        import ssl

        try:
            ctx = ssl.create_default_context()
        except Exception:
            ctx = ssl._create_unverified_context()

        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        return e.code == 200
    except Exception:
        pass

    try:
        import requests
        response = requests.get(url, headers=headers, timeout=(3.5, 4.0))
        return response.status_code == 200
    except Exception:
        return False


def _check_discord_intents(token: str) -> dict:
    res = {
        "checked": False,
        "all_enabled": True,
        "missing": [],
    }

    if not token or not str(token).strip():
        return res

    clean_token = str(token).strip().strip('"\'')
    if clean_token.lower().startswith("bot "):
        clean_token = clean_token[4:].strip()

    url = "https://discord.com/api/v10/applications/@me"
    headers = {
        "Authorization": f"Bot {clean_token}",
        "User-Agent": "DiscordBot (https://github.com/obgwew, v1.0)",
    }

    raw_data = None
    try:
        import urllib.request
        import ssl
        try:
            ctx = ssl.create_default_context()
        except Exception:
            ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=6, context=ctx) as resp:
            if resp.status == 200:
                raw_data = json.loads(resp.read().decode('utf-8'))
    except Exception:
        try:
            import requests
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                raw_data = r.json()
        except Exception:
            pass

    if raw_data and isinstance(raw_data, dict):
        flags = raw_data.get("flags") or 0
        
        has_presence = bool(flags & ((1 << 12) | (1 << 13)))
        has_members  = bool(flags & ((1 << 14) | (1 << 15)))
        has_content  = bool(flags & ((1 << 18) | (1 << 19)))

        missing = []
        if not has_presence:
            missing.append("Presence Intent")
        if not has_members:
            missing.append("Server Members Intent")
        if not has_content:
            missing.append("Message Content Intent")

        res["checked"] = True
        res["missing"] = missing
        res["all_enabled"] = len(missing) == 0

    return res


def _read_new_txt() -> str:
    path = os.path.normpath(NEW_TXT_PATH)
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            return text if text else _t('no_updates')
        except Exception:
            return _t('read_error')
    return _t('no_file')


def _ink_btn(content: ft.Control, bgcolor: str, on_click,
             border_radius: int = 10, padding=None, width=None) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=bgcolor,
        border_radius=border_radius,
        padding=padding or ft.Padding(left=24, top=11, right=24, bottom=11),
        on_click=on_click,
        ink=True,
        width=width,
        alignment=ft.Alignment(0, 0),
    )


def _soft_shadow(blur: int = 16, dy: int = 6, opacity: float = 0.10) -> ft.BoxShadow:
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=blur,
        color=ft.Colors.with_opacity(opacity, '#000000'),
        offset=ft.Offset(0, dy),
    )


def _card(content: ft.Control, bgcolor: str, border_color: str,
          radius: int = 14, padding=None, expand=False) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=bgcolor,
        border=ft.Border(
            left=ft.BorderSide(1, border_color), top=ft.BorderSide(1, border_color),
            right=ft.BorderSide(1, border_color), bottom=ft.BorderSide(1, border_color),
        ),
        border_radius=radius,
        padding=padding or ft.Padding(left=16, top=14, right=16, bottom=14),
        shadow=_soft_shadow(),
        expand=expand,
    )


_TABS = [
    ('main',      ft.Icons.HOME_ROUNDED,      'tab_main'),
    ('commands',  ft.Icons.CODE_ROUNDED,      'tab_commands'),
    ('variables', ft.Icons.TUNE_ROUNDED,      'tab_variables'),
    ('wiki',      ft.Icons.MENU_BOOK_ROUNDED,  'tab_wiki'),
    ('settings',  ft.Icons.SETTINGS_ROUNDED,  'tab_settings'),
]

_TAB_TITLE_KEYS = {tab_id: label_key for tab_id, _, label_key in _TABS}


class BotMainTab:

    def __init__(self, page: ft.Page):
        self._page          = page
        self._server_online = False
        self._busy          = False
        self._verifying     = False
        self._start_gen     = 0
        self._bot_data      = {}

        self._mobile_warn_btn = ft.Container(
            content=ft.Icon(ft.Icons.PRIORITY_HIGH_ROUNDED, size=15, color=_c('warning')),
            width=28,
            height=28,
            border_radius=14,
            bgcolor=_c('card_bg'),
            border=ft.Border(
                left=ft.BorderSide(1, _c('card_border')),
                top=ft.BorderSide(1, _c('card_border')),
                right=ft.BorderSide(1, _c('card_border')),
                bottom=ft.BorderSide(1, _c('card_border')),
            ),
            alignment=ft.Alignment(0, 0),
            on_click=self._show_mobile_warning,
            tooltip=_t('mobile_warn_title'),
            ink=True,
            visible=is_mobile(),
        )

        self._avatar_ctrl = ft.Container(
            content=ft.Text(_t('avatar_none'), size=13, color=_c('text_dim'),
                            text_align=ft.TextAlign.CENTER),
            width=96, height=96,
            border_radius=48,
            bgcolor=_c('card_border'),
            alignment=ft.Alignment(0, 0),
            border=ft.Border(
                left=ft.BorderSide(3, _c('accent')), top=ft.BorderSide(3, _c('accent')),
                right=ft.BorderSide(3, _c('accent')), bottom=ft.BorderSide(3, _c('accent')),
            ),
            shadow=_soft_shadow(blur=18, dy=8, opacity=0.16),
            on_long_press=self._show_change_avatar_dialog,
        )
        self._avatar_picker = ft.FilePicker()

        self._name_text = ft.Text(
            '', size=18, weight=ft.FontWeight.BOLD,
            color=_c('text'), text_align=ft.TextAlign.CENTER,
        )

        self._invite_icon  = ft.Icon(ft.Icons.OPEN_IN_BROWSER, color='#FFFFFF', size=18)
        self._invite_label = ft.Text(_t('invite_bot'), color='#FFFFFF', size=14,
                                     weight=ft.FontWeight.W_500)
        self._invite_btn = _ink_btn(
            content=ft.Row([self._invite_icon, self._invite_label],
                           spacing=8, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=_c('btn_invite'),
            on_click=self._invite_bot,
            width=210,
        )

        self._srv_dot = ft.Container(
            width=10, height=10, border_radius=5,
            bgcolor=_c('offline'),
        )
        self._srv_state = ft.Text(
            'Offline', size=12, color=_c('offline'), weight=ft.FontWeight.W_700,
        )
        self._srv_icon_wrap = ft.Container(
            content=ft.Icon(ft.Icons.DNS_ROUNDED, size=16, color=_c('text_dim')),
            width=28, height=28, border_radius=8,
            bgcolor=_c('bg'), alignment=ft.Alignment(0, 0),
        )
        self._srv_card = _card(
            content=ft.Column(
                [
                    ft.Row([self._srv_icon_wrap, self._srv_dot], spacing=6,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(_t('state_server'),
                            size=11, color=_c('text_dim'), weight=ft.FontWeight.W_500),
                    self._srv_state,
                ],
                spacing=4,
            ),
            bgcolor=_c('card_bg'), border_color=_c('card_border'),
            radius=12, padding=ft.Padding(left=12, top=10, right=12, bottom=10),
            expand=True,
        )

        self._guild_count_text = ft.Text('—', size=15, color=_c('text'),
                                          weight=ft.FontWeight.BOLD)
        self._guild_refresh_icon = ft.Icon(ft.Icons.REFRESH_ROUNDED, size=15,
                                            color=_c('text_dim'))
        self._guild_icon_wrap = ft.Container(
            content=ft.Icon(ft.Icons.GROUPS_ROUNDED, size=16, color=_c('text_dim')),
            width=28, height=28, border_radius=8,
            bgcolor=_c('bg'), alignment=ft.Alignment(0, 0),
        )
        self._guild_card = _card(
            content=ft.Column(
                [
                    ft.Row([self._guild_icon_wrap, ft.Container(expand=True),
                            self._guild_refresh_icon],
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(_t('servers_count'),
                            size=11, color=_c('text_dim'), weight=ft.FontWeight.W_500),
                    self._guild_count_text,
                ],
                spacing=4,
            ),
            bgcolor=_c('card_bg'), border_color=_c('card_border'),
            radius=12, padding=ft.Padding(left=12, top=10, right=12, bottom=10),
            expand=True,
        )
        self._guild_card.on_click  = self._refresh_guild_count
        self._guild_card.ink       = True

        self._status_row = ft.Row(
            [self._srv_card, self._guild_card], spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        self._intents_warn_text = ft.Text(
            _t('intents_warning_msg'),
            size=12,
            color=_c('warning'),
            expand=True,
        )

        self._open_dev_portal_btn = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED, size=14, color='#FFFFFF'),
                    ft.Text(
                        _t('open_dev_portal'),
                        size=11,
                        color='#FFFFFF',
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor=_c('warning'),
            border_radius=8,
            padding=ft.Padding(left=10, top=6, right=10, bottom=6),
            on_click=self._open_discord_dev_portal,
            ink=True,
        )

        self._intents_warning_card = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=20, color=_c('warning')),
                            ft.Text(
                                _t('intents_warning_title'),
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color=_c('warning'),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self._intents_warn_text,
                    ft.Row([self._open_dev_portal_btn], alignment=ft.MainAxisAlignment.END),
                ],
                spacing=8,
            ),
            bgcolor=ft.Colors.with_opacity(0.12, _c('warning')),
            border=ft.Border(
                left=ft.BorderSide(1.5, _c('warning')),
                top=ft.BorderSide(1.5, _c('warning')),
                right=ft.BorderSide(1.5, _c('warning')),
                bottom=ft.BorderSide(1.5, _c('warning')),
            ),
            border_radius=12,
            padding=ft.Padding(left=14, top=12, right=14, bottom=12),
            visible=False,
        )

        self._toggle_icon      = ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, color='#FFFFFF', size=20)
        self._toggle_icon_slot = ft.Container(content=self._toggle_icon,
                                               alignment=ft.Alignment(0, 0))
        self._toggle_label     = ft.Text(_t('start'), color='#FFFFFF', size=14,
                                         weight=ft.FontWeight.W_500)
        self._toggle_container = _ink_btn(
            content=ft.Row([self._toggle_icon_slot, self._toggle_label],
                           spacing=8, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=_c('success'),
            on_click=self._toggle_server,
            width=260,
            padding=ft.Padding(left=25, top=13, right=20, bottom=13),
        )
        self._toggle_container.border_radius = 12
        self._toggle_container.shadow = _soft_shadow(blur=14, dy=5, opacity=0.18)

        self._verify_icon      = ft.Icon(ft.Icons.VERIFIED_ROUNDED, color='#FFFFFF', size=18)
        self._verify_icon_slot = ft.Container(content=self._verify_icon,
                                               alignment=ft.Alignment(0, 0))
        self._verify_btn = _ink_btn(
            content=self._verify_icon_slot,
            bgcolor=_c('accent'),
            on_click=self._verify_token,
            width=46,
            padding=ft.Padding(left=0, top=0, right=0, bottom=0),
        )
        self._verify_btn.height = 46
        self._verify_btn.border_radius = 12
        self._verify_btn.tooltip = _t('verify_token')
        self._verify_btn.shadow = _soft_shadow(blur=14, dy=5, opacity=0.18)

        self._news_text = ft.Text(_read_new_txt(), size=13, color=_c('text_dim'))

        local_srv, _ = self._bot_client()
        if local_srv and hasattr(local_srv, 'register_state_listener'):
            local_srv.register_state_listener(self._on_server_state_changed)

        ThemeEngine.subscribe(self._on_theme)

    def dispose(self):
        _theme_unsub(self._on_theme)
        srv, _ = self._bot_client()
        unreg = getattr(srv, 'unregister_state_listener', None)
        if callable(unreg):
            try:
                unreg(self._on_server_state_changed)
            except Exception:
                pass

    def _token(self) -> str:
        return (
            TokenVault.get_cached_for_dir(self._bot_data.get('bot_dir', ''))
            or self._bot_data.get('token', '')
            or ''
        )

    async def _open_discord_dev_portal(self, _):
        bot_id = _get_bot_id_from_token(self._token())
        if bot_id:
            url = f"https://discord.com/developers/applications/{bot_id}/bot"
        else:
            url = "https://discord.com/developers/applications"
        await self._page.launch_url(url)

    def _check_privileged_intents_bg(self):
        token = self._token()

        if not token:
            self._intents_warning_card.visible = False
            try: self._page.update()
            except Exception: pass
            return

        def work():
            data = _check_discord_intents(token)
            if data.get('checked'):
                if not data.get('all_enabled'):
                    missing_str = ", ".join(data.get("missing", []))
                    self._intents_warn_text.value = _t('intents_missing_msg').format(missing=missing_str)
                    self._intents_warning_card.visible = True
                else:
                    self._intents_warning_card.visible = False
                try:
                    self._page.update()
                except Exception:
                    pass

        _run_bg(self._page, work)

    def _show_mobile_warning(self, _):
        def _close(_):
            self._page.pop_dialog()

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=_c('popup_bg'),
            shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=_c('warning'), size=24),
                    ft.Text(
                        _t('mobile_warn_title'),
                        weight=ft.FontWeight.BOLD,
                        color=_c('text'),
                        size=16,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Text(
                _t('mobile_warn_body'),
                color=_c('text_dim'),
                size=13,
            ),
            actions=[
                ft.FilledButton(
                    content=ft.Text(_t('ok'), color='#FFFFFF', weight=ft.FontWeight.BOLD),
                    on_click=_close,
                    style=ft.ButtonStyle(
                        bgcolor=_c('accent'),
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding(left=18, top=8, right=18, bottom=8),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.show_dialog(dlg)

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

    def _set_online_state(self, online: bool):
        self._server_online = online
        if online:
            self._srv_dot.bgcolor          = _c('online')
            self._srv_state.value          = _t('online')
            self._srv_state.color          = _c('online')
            self._toggle_icon.name         = ft.Icons.STOP_ROUNDED
            self._toggle_label.value       = _t('stop')
            self._toggle_container.bgcolor = _c('danger')
        else:
            self._srv_dot.bgcolor          = _c('offline')
            self._srv_state.value          = _t('offline')
            self._srv_state.color          = _c('offline')
            self._toggle_icon.name         = ft.Icons.PLAY_ARROW_ROUNDED
            self._toggle_label.value       = _t('start')
            self._toggle_container.bgcolor = _c('success')
            self._guild_count_text.value   = '—'
        
        self._toggle_icon_slot.content  = self._toggle_icon
        self._toggle_container.disabled = False
        self._toggle_container.opacity  = 1.0

    def _on_server_state_changed(self, is_online: bool):
        self._busy = False
        self._set_online_state(is_online)
        if is_online:
            self._fetch_guild_count(apply=True)
        else:
            srv, _ = self._bot_client()
            consume = getattr(srv, 'consume_last_error', None)
            err = consume() if callable(consume) else ''
            if err:
                self._notify(err, _c('danger'))
        try:
            self._page.update()
        except Exception:
            pass

    @staticmethod
    def _bot_client():
        try:
            from main_app.core_fdsb import Server
            _CORE_ERR['msg'] = ''
            return Server, getattr(Server, '_client', None)
        except Exception as e:
            import traceback
            traceback.print_exc()
            _CORE_ERR['msg'] = f'{type(e).__name__}: {e}'
            return None, None

    def _client_is_ready(self) -> bool:
        _, client = self._bot_client()
        if client is None:
            return False
        try:
            return (not client.is_closed()) and client.is_ready()
        except Exception:
            return False

    def _client_guild_count(self):
        _, client = self._bot_client()
        if client is None:
            return None
        try:
            if not client.is_closed():
                return len(client.guilds)
        except Exception:
            pass
        return None

    def _set_busy(self, going_online: bool):
        self._busy = True
        self._toggle_container.disabled = True
        self._toggle_container.opacity  = 0.70
        self._toggle_icon_slot.content  = ft.ProgressRing(
            width=16, height=16, stroke_width=2, color='#FFFFFF',
        )
        self._toggle_label.value = (
            _t('starting') if going_online
            else _t('stopping')
        )
        try:
            self._page.update()
        except Exception:
            pass

    def _toggle_server(self, _):
        if self._busy:
            return
        going_online = not self._server_online
        self._set_busy(going_online)

        def work():
            local_server, _ = self._bot_client()
            if not local_server:
                self._busy = False
                self._set_online_state(False)
                self._notify(
                    f"Bot engine failed to load: {_CORE_ERR['msg'] or 'unknown error'}",
                    _c('danger'),
                )
                try: self._page.update()
                except Exception: pass
                return

            try:
                local_server.set_flet_page(self._page)
                if going_online:
                    if self._page.platform.value in ('android', 'ios'):
                        try:
                            self._page.run_task(
                                local_server.request_flet_permissions, self._page,
                            )
                        except Exception:
                            pass

                    started = local_server.start_bot(
                        self._bot_data.get('bot_dir', ''), token=self._token(),
                    )
                    if not started:
                        self._busy = False
                        self._set_online_state(False)
                        consume = getattr(local_server, 'consume_last_error', None)
                        self._notify(
                            (consume() if callable(consume) else '')
                            or 'Bot did not start (start_bot returned False). '
                               'Check the token, intents and console output.',
                            _c('danger'),
                        )
                        try: self._page.update()
                        except Exception: pass
                    else:
                        self._arm_start_watchdog()
                else:
                    local_server.stop_bot()
                    self._busy = False
                    self._set_online_state(False)
                    try: self._page.update()
                    except Exception: pass
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f'[Dashboard] toggle failed: {e}')
                self._busy = False
                self._set_online_state(self._server_online)
                self._notify(f'Bot start/stop failed: {type(e).__name__}: {e}', _c('danger'))
                try: self._page.update()
                except Exception: pass

        _run_bg(self._page, work)

    def _arm_start_watchdog(self, timeout: float = 60.0):
        """If the bot never reports ready (e.g. login failed / missing intents),
        don't leave the button stuck on 'Starting...' forever."""
        self._start_gen += 1
        gen = self._start_gen

        def check():
            if gen != self._start_gen or not self._busy:
                return
            if self._client_is_ready():
                self._on_server_state_changed(True)
                return
            self._busy = False
            self._set_online_state(False)
            self._notify(
                'Bot did not become ready in time. Check the token, '
                'Privileged Gateway Intents and the console output.',
                _c('danger'),
            )
            try: self._page.update()
            except Exception: pass

        timer = threading.Timer(timeout, check)
        timer.daemon = True
        timer.start()

    def _verify_token(self, _):
        if self._verifying:
            return

        token = self._token()

        if not token or not str(token).strip():
            self._notify(_t('token_required'), _c('danger'))
            return

        self._verifying = True
        self._verify_btn.disabled = True
        self._verify_btn.opacity  = 0.70
        self._verify_btn.tooltip  = _t('verifying')
        self._verify_icon_slot.content = ft.ProgressRing(
            width=14, height=14, stroke_width=2, color='#FFFFFF',
        )
        try:
            self._page.update()
        except Exception:
            pass

        def work():
            is_valid = False
            try:
                is_valid = _validate_discord_token(token)
            except Exception as ex:
                print(f'[Dashboard] token verification error: {ex}')
                is_valid = False
            finally:
                self._verifying = False
                self._verify_btn.disabled = False
                self._verify_btn.opacity  = 1.0
                self._verify_btn.tooltip  = _t('verify_token')
                self._verify_icon_slot.content = self._verify_icon

                try:
                    if is_valid:
                        self._notify(_t('token_valid'), _c('success'))
                        self._check_privileged_intents_bg()
                    else:
                        self._notify(_t('token_invalid'), _c('danger'))
                except Exception:
                    pass

                try:
                    self._page.update()
                except Exception:
                    pass

        _run_bg(self._page, work)

    def _fetch_guild_count(self, apply: bool = False):
        count = str(self._client_guild_count()) if self._client_is_ready() else '—'
        if apply:
            self._guild_count_text.value = count
        return count

    def _refresh_guild_count(self, _):
        if not self._server_online:
            return
        self._guild_count_text.value = '…'
        try:
            self._page.update()
        except Exception:
            pass

        def work():
            self._fetch_guild_count(apply=True)
            try:
                self._page.update()
            except Exception:
                pass

        _run_bg(self._page, work)

    def _on_theme(self, data: dict):
        get = lambda k: data.get(k, '#888888')
        self._name_text.color        = get('text')
        self._news_text.color        = get('text_dim')
        self._invite_btn.bgcolor     = get('btn_invite')
        self._verify_btn.bgcolor     = get('accent')
        self._avatar_ctrl.border     = ft.Border(
            left=ft.BorderSide(3, get('accent')), top=ft.BorderSide(3, get('accent')),
            right=ft.BorderSide(3, get('accent')), bottom=ft.BorderSide(3, get('accent')),
        )
        for card, icon_wrap in ((self._srv_card, self._srv_icon_wrap),
                                 (self._guild_card, self._guild_icon_wrap)):
            card.bgcolor = get('card_bg')
            card.border  = ft.Border(
                left=ft.BorderSide(1, get('card_border')), top=ft.BorderSide(1, get('card_border')),
                right=ft.BorderSide(1, get('card_border')), bottom=ft.BorderSide(1, get('card_border')),
            )
            icon_wrap.bgcolor = get('bg')
        self._guild_count_text.color   = get('text')
        self._guild_refresh_icon.color = get('text_dim')
        self._mobile_warn_btn.bgcolor  = get('card_bg')
        self._mobile_warn_btn.border   = ft.Border(
            left=ft.BorderSide(1, get('card_border')), top=ft.BorderSide(1, get('card_border')),
            right=ft.BorderSide(1, get('card_border')), bottom=ft.BorderSide(1, get('card_border')),
        )
        self._intents_warning_card.bgcolor = ft.Colors.with_opacity(0.12, get('warning'))
        self._intents_warning_card.border = ft.Border(
            left=ft.BorderSide(1.5, get('warning')),
            top=ft.BorderSide(1.5, get('warning')),
            right=ft.BorderSide(1.5, get('warning')),
            bottom=ft.BorderSide(1.5, get('warning')),
        )
        self._intents_warn_text.color = get('warning')
        self._open_dev_portal_btn.bgcolor = get('warning')
        self._set_online_state(self._server_online)
        self._page.update()

    def build(self) -> ft.Control:
        if self._avatar_picker not in self._page.services:
            self._page.services.append(self._avatar_picker)

        avatar_section = ft.Stack(
            [
                ft.Row([self._avatar_ctrl], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(
                    content=self._mobile_warn_btn,
                    top=0,
                    left=0,
                ),
            ],
        )

        top_section = ft.Container(
            content=ft.Column(
                [
                    avatar_section,
                    ft.Row([self._name_text], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Row([self._invite_btn], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Row(
                        [self._toggle_container, self._verify_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    self._status_row,
                    self._intents_warning_card,
                    ft.Divider(color=_c('divider')),
                    ft.Text(_t('whats_new'), size=15,
                            weight=ft.FontWeight.BOLD, color=_c('text')),
                ],
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            padding=ft.Padding(left=16, top=16, right=16, bottom=0),
        )

        news_card = _card(
            content=ft.Column([self._news_text], scroll=ft.ScrollMode.AUTO),
            bgcolor=_c('card_bg'), border_color=_c('card_border'),
            radius=12, padding=ft.Padding(left=16, top=12, right=16, bottom=12),
        )
        news_card.margin = ft.Margin(left=16, top=8, right=16, bottom=16)
        news_card.height = 260

        return ft.Column(
            [top_section, news_card],
            spacing=0,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _set_avatar(self, img_path: str):
        if img_path and os.path.isfile(img_path):
            self._avatar_ctrl.content = ft.Image(
                src=img_path, width=96, height=96,
                fit=ft.BoxFit.COVER,
                border_radius=48,
            )
            self._avatar_ctrl.bgcolor = None
        else:
            self._avatar_ctrl.content = ft.Text(
                _t('avatar_none'), size=13, color=_c('text_dim'),
                text_align=ft.TextAlign.CENTER,
            )
            self._avatar_ctrl.bgcolor = _c('card_border')

    def load_bot(self, bot_data: dict):
        self._bot_data        = bot_data
        self._name_text.value = bot_data.get('name', 'Bot')

        self._set_avatar(bot_data.get('image', ''))

        is_online = self._client_is_ready()
        self._set_online_state(is_online)
        if is_online:
            self._fetch_guild_count(apply=True)
        self._news_text.value = _read_new_txt()

        self._check_privileged_intents_bg()


    def _show_change_avatar_dialog(self, _):
        if not self._bot_data.get('bot_dir'):
            return

        cur = self._bot_data.get('image', '')
        if cur and os.path.isfile(cur):
            preview_content = ft.Image(
                src=cur, width=96, height=96,
                fit=ft.BoxFit.COVER, border_radius=48,
            )
            preview_bg = None
        else:
            preview_content = ft.Text(
                _t('avatar_none'), size=13, color=_c('text_dim'),
                text_align=ft.TextAlign.CENTER,
            )
            preview_bg = _c('card_border')

        preview = ft.Container(
            content=preview_content,
            width=96, height=96, border_radius=48,
            bgcolor=preview_bg, alignment=ft.Alignment(0, 0),
        )

        def _close(_):
            self._page.pop_dialog()

        async def _choose(_):
            self._page.pop_dialog()
            await self._pick_and_apply_avatar()

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=_c('popup_bg'),
            shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Text(
                _t('avatar_change_title'),
                weight=ft.FontWeight.BOLD, color=_c('text'), size=16,
            ),
            content=ft.Column(
                [
                    ft.Row([preview], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Text(
                        _t('avatar_change_body'),
                        color=_c('text_dim'), size=13,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                tight=True, spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text(_t('cancel'),
                                    color=_c('text_dim')),
                    on_click=_close,
                ),
                ft.FilledButton(
                    content=ft.Text(
                        _t('avatar_choose_btn'),
                        color='#FFFFFF', weight=ft.FontWeight.BOLD,
                    ),
                    on_click=_choose,
                    style=ft.ButtonStyle(
                        bgcolor=_c('accent'),
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding(left=18, top=8, right=18, bottom=8),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.show_dialog(dlg)

    async def _pick_and_apply_avatar(self):
        bot_dir = self._bot_data.get('bot_dir', '')
        if not bot_dir:
            return

        fail_msg = _t('avatar_change_failed')

        try:
            files = await self._avatar_picker.pick_files(
                dialog_title=_t('avatar_pick_title'),
                file_type=ft.FilePickerFileType.IMAGE,
                allow_multiple=False,
            )
        except Exception as e:
            print(f'[Dashboard] avatar pick failed: {e}')
            self._notify(fail_msg, _c('danger'))
            return

        if not files:
            return

        src = getattr(files[0], 'path', None)
        ext = os.path.splitext(getattr(files[0], 'name', '') or src or '')[1].lower()

        if ext not in _AVATAR_EXTS:
            self._notify(
                _t('avatar_invalid_type'),
                _c('danger'),
            )
            return
        if not src or not os.path.isfile(src):
            self._notify(fail_msg, _c('danger'))
            return

        bot_files_dir = os.path.join(bot_dir, 'bot_files')
        config_path   = os.path.join(bot_files_dir, 'config.json')
        new_path = os.path.join(bot_files_dir, f'avatar_{int(time.time() * 1000)}{ext}')
        old_path = self._bot_data.get('image', '')

        try:
            os.makedirs(bot_files_dir, exist_ok=True)
            shutil.copyfile(src, new_path)
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            cfg['image'] = new_path
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'[Dashboard] avatar save failed: {e}')
            try:
                if os.path.isfile(new_path):
                    os.remove(new_path)
            except Exception:
                pass
            self._notify(fail_msg, _c('danger'))
            return

        try:
            if (old_path and old_path != new_path
                    and os.path.basename(old_path).startswith('avatar_')
                    and os.path.dirname(os.path.abspath(old_path)) == os.path.abspath(bot_files_dir)
                    and os.path.isfile(old_path)):
                os.remove(old_path)
        except Exception:
            pass

        self._bot_data['image'] = new_path
        self._set_avatar(new_path)
        self._page.update()
        self._notify(
            _t('avatar_changed'),
            _c('success'),
        )

    async def _invite_bot(self, e):
        bot_id = _get_bot_id_from_token(self._token())
        if bot_id:
            url = f'https://discord.com/oauth2/authorize?client_id={bot_id}&permissions=8&scope=bot'
            await self._page.launch_url(url)


# ══════════════════════════════════════════════════════════════════════════════
#  BotDashboardScreen 
# ══════════════════════════════════════════════════════════════════════════════

class BotDashboardScreen:
    def __init__(self, page: ft.Page, bot_dir: str = '', on_back=None):
        self._page    = page
        self._on_back = on_back
        self._active  = 'main'
        self._return_to = None   # tab we jumped from (e.g. editor -> wiki), so Back returns there
        self._bot_dir = bot_dir
        self._tab_containers: dict[str, ft.Container] = {}

        self._title_text = ft.Text(
            '', size=16, weight=ft.FontWeight.BOLD,
            color=_c('text'),
            text_align=ft.TextAlign.CENTER,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        self._back_btn = ft.IconButton(
            icon=ft.Icons.ARROW_BACK_ROUNDED,
            icon_color='#FFFFFF',
            bgcolor=_c('accent'),
            on_click=lambda _: self._on_back and self._on_back(),
            icon_size=16,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            visible=True,
        )

        self._tab_views: dict = {}   # created lazily in _view()

        self._tab_ids = [t[0] for t in _TABS]

        self._slider = SlideStack(page)
        self._swipe  = SwipeController(
            page, self._slider,
            neighbour=self._swipe_neighbour,
            can_swipe=self._swipe_allowed,
            on_commit=self._swipe_commit,
        )

        self._nav_bar = self._build_nav()

        if bot_dir:
            self.load_bot(bot_dir)
        else:
            self._update_title()

        ThemeEngine.subscribe(self._on_theme)

    def _update_title(self):
        title_key = _TAB_TITLE_KEYS.get(self._active, 'tab_main')
        self._title_text.value = _t(title_key)

    def _go_to_wiki_events(self):
        origin = self._active
        self._view('wiki').select_events_filter()
        self._switch_tab('wiki')
        if origin != 'wiki':
            self._return_to = origin   # set after _switch_tab (which clears it)

    def handle_back(self) -> bool:
        # 1) deepest level first: editor / folder / detail inside the active tab
        active_tab = self._tab_views.get(self._active)
        if active_tab and hasattr(active_tab, 'handle_back'):
            if active_tab.handle_back():
                return True

        # 2) we arrived here from another tab (e.g. editor -> wiki): go back to it
        if self._return_to and self._return_to != self._active:
            target, self._return_to = self._return_to, None
            self._switch_tab(target)
            return True

        # 3) every tab sits directly under the bot list: let the app go there
        return False

    def _on_theme(self, data: dict):
        get = lambda k: data.get(k, '#888888')
        self._title_text.color        = get('text')
        self._back_btn.bgcolor        = get('accent')
        self._nav_bar.bgcolor         = get('nav_bg')
        self._nav_bar.indicator_color = get('nav_active')
        if hasattr(self, '_header'):
            self._header.bgcolor      = get('card_bg')
            self._header.border       = ft.Border(bottom=ft.BorderSide(1, get('divider')))

        self._update_title()
        self._nav_bar.destinations = self._build_destinations()
        self._page.update()

    def _read_bot_data(self) -> dict:
        try:
            with open(os.path.join(self._bot_dir, 'bot_files', 'config.json'), 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['bot_dir'] = self._bot_dir
            return data
        except Exception as e:
            print(f'[Dashboard] failed to read config.json: {e}')
            return {}

    def _view(self, tab_id: str):
        view = self._tab_views.get(tab_id)
        if view is not None:
            return view
        page = self._page
        if tab_id == 'main':
            view = BotMainTab(page)
        elif tab_id == 'commands':
            view = BotCommandsTab(page, on_wiki_events_req=self._go_to_wiki_events)
        elif tab_id == 'variables':
            view = BotVariablesTab(page)
        elif tab_id == 'settings':
            view = BotSettingsTab(
                page,
                on_lang_change=self._on_settings_lang_change,
                on_theme_change=self._on_settings_theme_change,
            )
        else:
            view = BotWikiTab(page)
        self._tab_views[tab_id] = view
        if self._bot_dir:
            if tab_id in ('commands', 'variables'):
                view.load_bot(os.path.join(self._bot_dir, 'bot_files'))
            else:
                view.load_bot(self._read_bot_data())
        return view

    def _notify(self, tab_id: str, hook: str):
        fn = getattr(self._tab_views.get(tab_id), hook, None)
        if callable(fn):
            fn()

    def _dispose_tabs(self):
        for view in list(self._tab_views.values()):
            fn = getattr(view, 'dispose', None)
            if callable(fn):
                try:
                    fn()
                except Exception as e:
                    print(f'[Dashboard] tab dispose failed: {e}')
        self._tab_views.clear()
        self._tab_containers.clear()

    def dispose(self):
        self._dispose_tabs()
        _theme_unsub(self._on_theme)

    def _rebuild_all_tabs(self, update_nav: bool):
        active = self._active
        self._dispose_tabs()

        self._update_title()

        if update_nav:
            self._nav_bar.destinations = self._build_destinations()

        self._switch_tab(active, animate=False)
        self._notify(active, 'on_show')
        self._page.update()

    def _on_settings_lang_change(self, lang: str):
        self._rebuild_all_tabs(update_nav=True)

    def _on_settings_theme_change(self, theme_key: str):
        self._rebuild_all_tabs(update_nav=False)

    def build(self) -> ft.Control:
        # Header using Stack to guarantee absolute center alignment of title
        self._header = ft.Container(
            content=ft.Stack(
                controls=[
                    ft.Container(
                        content=self._title_text,
                        alignment=ft.Alignment(0, 0),
                        padding=ft.Padding(left=48, right=48, top=0, bottom=0),
                    ),
                    ft.Container(
                        content=self._back_btn,
                        alignment=ft.Alignment(-1, 0),
                        left=0,
                        top=0,
                        bottom=0,
                    ),
                ],
            ),
            bgcolor=_c('card_bg'),
            border=ft.Border(bottom=ft.BorderSide(1, _c('divider'))),
            padding=ft.Padding(left=14, top=6, right=14, bottom=6),
            height=52,
            shadow=_soft_shadow(blur=10, dy=2, opacity=0.06),
        )

        self._switch_tab('main', animate=False)

        return ft.Column(
            [self._header, self._swipe.control, self._nav_bar],
            spacing=0,
            expand=True,
        )

    def _build_destinations(self) -> list:
        return [
            ft.NavigationBarDestination(
                icon=icon,
                label=_t(label_key),
            )
            for _, icon, label_key in _TABS
        ]

    def _build_nav(self) -> ft.NavigationBar:
        return ft.NavigationBar(
            selected_index=0,
            bgcolor=_c('nav_bg'),
            indicator_color=_c('nav_active'),
            label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
            on_change=self._on_nav_change,
            destinations=self._build_destinations(),
        )

    def _on_nav_change(self, e):
        target_id  = self._tab_ids[e.control.selected_index]
        leaving_id = self._active

        if target_id == leaving_id:
            return

        def _do_switch():
            self._switch_tab(target_id)

        def _stay_on_current_tab():
            self._nav_bar.selected_index = self._tab_ids.index(leaving_id)
            self._page.update()

        leaving_view = self._tab_views.get(leaving_id)
        guard = getattr(leaving_view, 'guard_tab_change', None)
        if callable(guard):
            guard(_do_switch, _stay_on_current_tab)
        else:
            _do_switch()

    def _get_slot(self, tab_id: str) -> ft.Container:
        slot = self._tab_containers.get(tab_id)
        if slot is None:
            view_control = self._view(tab_id).build()
            slot = SlideStack.make_slot(view_control)
            self._tab_containers[tab_id] = slot
        return slot

    def _activate(self, tab_id: str):
        prev                         = self._active
        self._active                 = tab_id
        self._return_to              = None   # any manual/explicit switch forgets the jump origin
        self._nav_bar.selected_index = self._tab_ids.index(tab_id)
        self._back_btn.visible       = (tab_id == 'main')
        self._update_title()
        if prev != tab_id:
            self._notify(prev, 'on_hide')
            self._notify(tab_id, 'on_show')

    def _switch_tab(self, tab_id: str, animate: bool = True):
        slot      = self._get_slot(tab_id)
        direction = 0
        if animate and tab_id != self._active:
            direction = 1 if self._tab_ids.index(tab_id) > self._tab_ids.index(self._active) else -1
        self._activate(tab_id)
        self._slider.show_slot(slot, direction)

    # ── swipe between tabs ────────────────────────────────────────────────

    def _swipe_allowed(self) -> bool:
        view    = self._tab_views.get(self._active)
        blocked = getattr(view, 'swipe_blocked', None)
        return not (callable(blocked) and blocked())

    def _swipe_neighbour(self, side: int):
        idx = self._tab_ids.index(self._active) + side
        if 0 <= idx < len(self._tab_ids):
            return self._get_slot(self._tab_ids[idx])
        return None

    def _swipe_commit(self, side: int, finish):
        target = self._tab_ids[self._tab_ids.index(self._active) + side]

        def _go():
            self._activate(target)
            finish(True)

        def _stay():
            finish(False)

        guard = getattr(self._tab_views.get(self._active), 'guard_tab_change', None)
        if callable(guard):
            guard(_go, _stay)
        else:
            _go()

    def load_bot(self, bot_dir: str):
        self._bot_dir = bot_dir
        self._dispose_tabs()
        self._update_title()