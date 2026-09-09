# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/main.py . migrated to Flet 0.85.2+ / v1 API 

import os
import json
import base64
import threading
import time

import flet as ft

from main_app.settings import BotSettingsTab, get_current_lang, is_mobile
from main_app.commands_view import BotCommandsTab
from main_app.langs.translations import Translations
from main_app.theme.theme_engine import ThemeEngine
from main_app.variables_view import BotVariablesTab
from main_app.wiki_view import BotWikiTab

NEW_TXT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'main_app/new.txt'
)


def _t(key: str) -> str:
    return Translations.get(key, get_current_lang())

def _ar(text: str) -> str:
    return text

def _t_safe(key: str, fallback_en: str, fallback_ar: str = None) -> str:
    try:
        val = Translations.get(key, get_current_lang())
    except Exception:
        val = None
    if val and val != key:
        return val
    if get_current_lang() == 'ar' and fallback_ar:
        return fallback_ar
    return fallback_en


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
    """
    التحقق من صحة توكن ديسكورد مع مهلة محددة ودعم بيئة الجوال دون تعليق.
    يستخدم urllib القياسية المدمجة أولاً ثم requests كبديل احتياطي.
    """
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

    # 1. المحاولة باستخدام urllib القياسية (متوفرة دائماً في بايثون على كافة المنصات بدون تبعيات)
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
        # في حال استجاب ديسكورد برمز 401 (توكن غير صحيح) فهذا رد ناجح يؤكد عدم صحة التوكن
        return e.code == 200
    except Exception:
        pass

    # 2. بديل احتياطي باستخدام requests إن توفرت
    try:
        import requests
        response = requests.get(url, headers=headers, timeout=(3.5, 4.0))
        return response.status_code == 200
    except Exception:
        return False


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
        animate_opacity=150,
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
    ('main',      ft.Icons.HOME_ROUNDED,     'tab_main'),
    ('commands',  ft.Icons.CODE_ROUNDED,     'tab_commands'),
    ('variables', ft.Icons.TUNE_ROUNDED,     'tab_variables'),
    ('wiki',      ft.Icons.MENU_BOOK_ROUNDED, 'tab_wiki'),
    ('settings',  ft.Icons.SETTINGS_ROUNDED, 'tab_settings'),
]


class BotMainTab:

    def __init__(self, page: ft.Page):
        self._page          = page
        self._server_online = False
        self._busy          = False
        self._verifying     = False
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
        )

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
                    ft.Text(_t_safe('status_bot_section', 'Server Status', 'حالة الخادم'),
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
                    ft.Text(_t_safe('servers_count', 'Servers', 'عدد السيرفرات'),
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
            width=160,
            padding=ft.Padding(left=20, top=13, right=20, bottom=13),
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
        
    async def _open_link(self, url: str):
        await self._page.launch_url(url)

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
            self._srv_state.value          = _t_safe('online', 'Online', 'متصل')
            self._srv_state.color          = _c('online')
            self._toggle_icon.name         = ft.Icons.STOP_ROUNDED
            self._toggle_label.value       = _t('stop')
            self._toggle_container.bgcolor = _c('danger')
        else:
            self._srv_dot.bgcolor          = _c('offline')
            self._srv_state.value          = _t_safe('offline', 'Offline', 'غير متصل')
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
        try:
            self._page.update()
        except Exception:
            pass

    @staticmethod
    def _bot_client():
        try:
            from main_app.core_fdsb import local_server
            return local_server, getattr(local_server, '_client', None)
        except Exception:
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
            _t_safe('starting', 'Connecting…', 'جاري الاتصال…') if going_online
            else _t_safe('stopping', 'Stopping…', 'جاري الإيقاف…')
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

                    started = local_server.start_bot(self._bot_data.get('bot_dir', ''))
                    if not started:
                        self._busy = False
                        self._set_online_state(False)
                        try: self._page.update()
                        except Exception: pass
                else:
                    local_server.stop_bot()
                    self._busy = False
                    self._set_online_state(False)
                    try: self._page.update()
                    except Exception: pass
            except Exception as e:
                print(f'[Dashboard] toggle failed: {e}')
                self._busy = False
                self._set_online_state(self._server_online)
                try: self._page.update()
                except Exception: pass

        _run_bg(self._page, work)

    def _verify_token(self, _):
        if self._verifying:
            return

        token = self._bot_data.get('token', '')

        # محاولة قراءة التوكن من config.json في حال لم يكن محملاً في الذاكرة
        if not token and self._bot_data.get('bot_dir'):
            try:
                cfg_path = os.path.join(self._bot_data['bot_dir'], 'bot_files', 'config.json')
                if os.path.isfile(cfg_path):
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        disk_cfg = json.load(f)
                    token = disk_cfg.get('token', '')
                    if token:
                        self._bot_data['token'] = token
            except Exception:
                pass

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
                # يضمن استرجاع حالة الزر دائماً وتفادي أي تعليق في الـ loop
                self._verifying = False
                self._verify_btn.disabled = False
                self._verify_btn.opacity  = 1.0
                self._verify_btn.tooltip  = _t('verify_token')
                self._verify_icon_slot.content = self._verify_icon

                try:
                    if is_valid:
                        self._notify(_t('token_valid'), _c('success'))
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
        self._set_online_state(self._server_online)
        self._page.update()

    def build(self) -> ft.Control:
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
                    self._status_row,
                    ft.Row(
                        [self._toggle_container, self._verify_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
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

    def load_bot(self, bot_data: dict):
        self._bot_data        = bot_data
        self._name_text.value = bot_data.get('name', 'Bot')

        img_path = bot_data.get('image', '')
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

        is_online = self._client_is_ready()
        self._set_online_state(is_online)
        if is_online:
            self._fetch_guild_count(apply=True)
        self._news_text.value = _read_new_txt()

    async def _invite_bot(self, e):
        bot_id = _get_bot_id_from_token(self._bot_data.get('token', ''))
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
        self._bot_dir = bot_dir

        self._title_text = ft.Text(
            '', size=16, weight=ft.FontWeight.BOLD,
            color=_c('text'), expand=True,
            text_align=ft.TextAlign.CENTER,
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

        self._main_tab      = BotMainTab(page)
        self._commands_tab  = BotCommandsTab(page, on_wiki_events_req=self._go_to_wiki_events)
        self._variables_tab = BotVariablesTab(page)
        self._settings_tab  = BotSettingsTab(
            page,
            on_lang_change=self._on_settings_lang_change,
            on_theme_change=self._on_settings_theme_change,
        )
        self._wiki_tab   = BotWikiTab(page)

        self._tab_views = {
            'main':      self._main_tab,
            'commands':  self._commands_tab,
            'variables': self._variables_tab,
            'settings':  self._settings_tab,
            'wiki':      self._wiki_tab,
        }

        self._tab_ids = [t[0] for t in _TABS]

        self._tab_containers: dict[str, ft.Container] = {}
        self._tabs_stack = ft.Stack(controls=[], expand=True)

        self._nav_bar = self._build_nav()

        if bot_dir:
            self.load_bot(bot_dir)

        ThemeEngine.subscribe(self._on_theme)

    def _go_to_wiki_events(self):
        self._wiki_tab.select_events_filter()
        self._switch_tab('wiki')

    def handle_back(self) -> bool:
        active_tab = self._tab_views.get(self._active)
        if active_tab and hasattr(active_tab, 'handle_back'):
            if active_tab.handle_back():
                return True

        if self._active != 'main':
            self._switch_tab('main')
            return True

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

        self._nav_bar.destinations = self._build_destinations()
        self._page.update()

    def _rebuild_all_tabs(self, update_nav: bool):
        self._main_tab      = BotMainTab(self._page)
        self._commands_tab  = BotCommandsTab(self._page, on_wiki_events_req=self._go_to_wiki_events)
        self._variables_tab = BotVariablesTab(self._page)
        self._settings_tab  = BotSettingsTab(
            self._page,
            on_lang_change=self._on_settings_lang_change,
            on_theme_change=self._on_settings_theme_change,
        )
        self._wiki_tab      = BotWikiTab(self._page)

        self._tab_views = {
            'main':      self._main_tab,
            'commands':  self._commands_tab,
            'variables': self._variables_tab,
            'settings':  self._settings_tab,
            'wiki':      self._wiki_tab,
        }

        self._tab_containers.clear()
        self._tabs_stack.controls.clear()

        if self._bot_dir:
            bot_files_dir = os.path.join(self._bot_dir, 'bot_files')
            config_path   = os.path.join(self._bot_dir, 'bot_files', 'config.json')
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    bot_data = json.load(f)
                bot_data['bot_dir'] = self._bot_dir
            except Exception:
                bot_data = {}

            self._title_text.value = bot_data.get('name', 'Bot')
            self._main_tab.load_bot(bot_data)
            self._commands_tab.load_bot(bot_files_dir)
            self._variables_tab.load_bot(bot_files_dir)
            self._settings_tab.load_bot(bot_data)
            self._wiki_tab.load_bot(bot_data)

        if update_nav:
            self._nav_bar.destinations = self._build_destinations()
            
        self._switch_tab(self._active)
        self._page.update()

    def _on_settings_lang_change(self, lang: str):
        self._rebuild_all_tabs(update_nav=True)

    def _on_settings_theme_change(self, theme_key: str):
        self._rebuild_all_tabs(update_nav=False)

    def build(self) -> ft.Control:
        self._header = ft.Container(
            content=ft.Row(
                [
                    self._back_btn,
                    self._title_text,
                    ft.Container(width=52),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            bgcolor=_c('card_bg'),
            border=ft.Border(bottom=ft.BorderSide(1, _c('divider'))),
            padding=ft.Padding(left=14, top=10, right=14, bottom=10),
            height=52,
            shadow=_soft_shadow(blur=10, dy=2, opacity=0.06),
        )

        self._switch_tab('main')

        return ft.Column(
            [self._header, self._tabs_stack, self._nav_bar],
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

    def _switch_tab(self, tab_id: str):
        if tab_id not in self._tab_containers:
            view_control = self._tab_views[tab_id].build()
            container = ft.Container(
                content=view_control,
                expand=True,
                visible=True
            )
            self._tab_containers[tab_id] = container
            self._tabs_stack.controls.append(container)

        for tid, ctrl in self._tab_containers.items():
            ctrl.visible = (tid == tab_id)

        self._active                 = tab_id
        self._nav_bar.selected_index = self._tab_ids.index(tab_id)
        self._back_btn.visible       = (tab_id == 'main')
        self._page.update()

    def load_bot(self, bot_dir: str):
        config_path = os.path.join(bot_dir, 'bot_files', 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                bot_data = json.load(f)
            bot_data['bot_dir'] = bot_dir
        except Exception as e:
            print(f'[Dashboard] failed to read config.json: {e}')
            bot_data = {}

        self._title_text.value = bot_data.get('name', 'Bot')

        bot_files_dir = os.path.join(bot_dir, 'bot_files')
        self._main_tab.load_bot(bot_data)
        self._commands_tab.load_bot(bot_files_dir)
        self._variables_tab.load_bot(bot_files_dir)
        self._settings_tab.load_bot(bot_data)
        self._wiki_tab.load_bot(bot_data)
        self._switch_tab('main')