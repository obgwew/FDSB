# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/settings.py . migrated to Flet 0.85.2+ / v1 API u

import os
import sys
import json
import time
import zipfile
import random
import shutil
import base64
import subprocess

import flet as ft

from main_app.langs.translations import Translations
from main_app.theme.theme_engine import ThemeEngine
from main_app.load.loading_view import LoadingScreen
from main_app.status.status_view import BotStatusView

def is_mobile() -> bool:
    return os.getenv('FLET_PLATFORM', '').lower() in ('android', 'ios')

def get_persistent_base_dir() -> str:
    storage_data = os.getenv('FLET_APP_STORAGE_DATA')
    if storage_data:
        return storage_data
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_app_data_dir() -> str:
    path = os.path.join(get_persistent_base_dir(), 'app_data')
    os.makedirs(path, exist_ok=True)
    return path

_SETTINGS_PATH = os.path.join(get_app_data_dir(), 'settings.json')

def load_settings() -> dict:
    try:
        with open(_SETTINGS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(patch: dict):
    data = load_settings()
    data.update(patch)
    try:
        with open(_SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'[Settings] save failed: {e}')

def get_current_theme() -> str:
    return load_settings().get('theme', 'system_wh')

def get_current_lang() -> str:
    return load_settings().get('lang', 'en')

def _pending_beta_flags(d: dict = None) -> int:
    if d is None:
        d = load_settings()
    _base  = len([k for k in d if not k.startswith('_')])
    _score = d.get('_ul', 0)
    return _base + _score

def _ui_profile_fixed() -> bool:
    return _pending_beta_flags() > 10

_FALLBACKS = {
    'general_section':       'General',
    'language':              'Language',
    'save':                  'Save',
    'design_section':        'Appearance',
    'info_section':          'Information',
    'github':                'GitHub',
    'discord':               'Discord',
    'link':                  '↗ Open link',
    'bot_name_hint':         'Bot Name',
    'bot_token_hint':        'Bot Token',
    'token_required':        'Token is required',
    'system_wh':             'System (Light)',
    'system_da':             'System (Dark)',
    'blue_sky':              'Blue Sky',
    'yellow_bile':           'Yellow',
    'v2_dark':               'Dark Gold',
    'export_section':        'Export Bot Data',
    'export_desc':           'Export commands and variables as a ZIP file',
    'export_zip':            'Export ZIP',
    'export_success':        'Exported successfully!',
    'no_bot_selected':       'No bot selected!',
    'folders_not_found':     'Folders not found!',
    'export_failed':         'Export failed!',
    'danger_zone':           'Danger Zone',
    'delete_bot_perm':       'Delete This Bot Permanently',
    'captcha_enter':         'Enter 3 digits',
    'captcha_hint':          'Enter the 3 digits shown above',
    'confirm_delete':        'Confirm Delete',
    'captcha_wrong':         'Incorrect code — try again',
    'status_bot_section':    'Bot Status',
    'status_bot_desc':       "Configure your bot's presence and rotating status messages",
    'open_status_bot':       'Manage Status',
    'search_lang':           'Search language...',
    'select_language':       'Select Language',
    'cancel':                'Cancel',
    'saved_successfully':    'Settings saved successfully!',
    'selfbot_token_blocked': 'User/Self-bot tokens are strictly prohibited for safety and security.',
    'invalid_bot_token':     'Invalid bot token. Please enter an official Discord Bot token.',
}

_LANG_DETAILS: dict[str, dict[str, str]] = {
    'ar': {'name': 'العربية',  'sub': 'Arabic',    'code': 'AR'},
    'en': {'name': 'English',  'sub': 'English',   'code': 'EN'},
    'fa': {'name': 'فارسی',    'sub': 'Persian',   'code': 'FA'},
    'ur': {'name': 'اردو',     'sub': 'Urdu',      'code': 'UR'},
    'fr': {'name': 'Français', 'sub': 'French',    'code': 'FR'},
    'de': {'name': 'Deutsch',  'sub': 'German',    'code': 'DE'},
    'tr': {'name': 'Türkçe',   'sub': 'Turkish',   'code': 'TR'},
    'ch': {'name': '中文',     'sub': 'Chinese',   'code': 'ZH'},
    'ru': {'name': 'Русский',  'sub': 'Russian',   'code': 'RU'},
    'pl': {'name': 'Polski',   'sub': 'Polish',    'code': 'PL'},
    'es': {'name': 'Español',  'sub': 'Spanish',   'code': 'ES'},
    'ja': {'name': '日本語',   'sub': 'Japanese',  'code': 'JA'},
    'hi': {'name': 'हिंदी',    'sub': 'Hindi',     'code': 'HI'},
}

def _t(key: str) -> str:
    lang = get_current_lang()
    val = Translations.get(key, lang)
    if val and val != key:
        return val
    return _FALLBACKS.get(key, key)

def _c(key: str) -> str:
    return ThemeEngine.hex(key)

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


ALL_THEMES = {
    'system_wh': {
        'swatch_a': '#1B1F2E',
        'swatch_b': '#ECF1FF',
        'data': {
            'bg':             '#FFFFFF',
            'card_bg':        '#E3E9FA',
            'card_border':    '#FFFFFF',
            'footer_bg':      '#D6E7FD',
            'popup_bg':       '#FFFFFF',
            'input_bg':       '#F0F3FA',
            'input_border':   '#C7D0E0',
            'text':           '#000000',
            'text_dim':       '#5C5C5C',
            'text_on_accent': '#FFFFFF',
            'accent':         '#1B1F2E',
            'accent_hover':   '#2C3150',
            'success':        '#16A34A',
            'danger':         '#DC2626',
            'icon_bg':        '#8F8F8F',
            'discord':        '#5865F2',
            'github':         '#24292E',
            'title_bcfd':     '#1B1F2E',
            'nav_bg':         '#E8EDFF',
            'nav_active':     '#000000',
            'nav_inactive':   '#555555',
            'divider':        '#E4E8F0',
            'online':         '#16A34A',
            'offline':        '#DC2626',
            'btn_invite':     '#5865F2',
        },
    },
    'blue_sky': {
        'swatch_a': '#0D47A1',
        'swatch_b': '#BBDEFB',
        'data': {
            'bg':             '#E8F6FF',
            'card_bg':        '#BBDEFB',
            'card_border':    '#90CAF9',
            'footer_bg':      '#90CAF9',
            'popup_bg':       '#E8F6FF',
            'input_bg':       '#64B5F6',
            'input_border':   '#42A5F5',
            'text':           '#0D47A1',
            'text_dim':       '#1565C0',
            'text_on_accent': '#FFFFFF',
            'accent':         '#0D47A1',
            'accent_hover':   '#1565C0',
            'success':        '#2E7D32',
            'danger':         '#C62828',
            'icon_bg':        '#64B5F6',
            'discord':        '#5865F2',
            'github':         '#0D47A1',
            'title_bcfd':     '#0D47A1',
            'nav_bg':         '#1565C0',
            'nav_active':     '#FFFFFF',
            'nav_inactive':   '#90CAF9',
            'divider':        '#90CAF9',
            'online':         '#2E7D32',
            'offline':        '#C62828',
            'btn_invite':     '#5865F2',
        },
    },
    'yellow_bile': {
        'swatch_a': '#FFFB00',
        'swatch_b': '#FFF7AD',
        'data': {
            'bg':             '#FFFDE7',
            'card_bg':        '#FFF9C4',
            'card_border':    '#FFE70C',
            'footer_bg':      '#FFEE58',
            'popup_bg':       '#FFFDE7',
            'input_bg':       '#FFFB28',
            'input_border':   '#FFB300',
            'text':           '#3E2723',
            'text_dim':       '#5D4037',
            'text_on_accent': '#FFFFFF',
            'accent':         '#E65100',
            'accent_hover':   '#BF360C',
            'success':        '#2E7D32',
            'danger':         '#B71C1C',
            'icon_bg':        '#FFCA28',
            'discord':        '#5865F2',
            'github':         '#3E2723',
            'title_bcfd':     '#E65100',
            'nav_bg':         '#F57F17',
            'nav_active':     '#FFFFFF',
            'nav_inactive':   '#FFF9C4',
            'divider':        '#F9A825',
            'online':         '#2E7D32',
            'offline':        '#B71C1C',
            'btn_invite':     '#5865F2',
        },
    },
    'system_da': {
        'swatch_a': "#6D6D6D",
        'swatch_b': "#1A1A1A",
        'data': {
            'bg':             '#1A1C26',
            'card_bg':        '#23263A',
            'card_border':    '#2E3250',
            'footer_bg':      '#1E2133',
            'popup_bg':       '#23263A',
            'input_bg':       '#2A2D40',
            'input_border':   '#3A3F5C',
            'text':           '#E8EAF6',
            'text_dim':       '#7B82A8',
            'text_on_accent': '#FFFFFF',
            'accent':         '#4A90D9',
            'accent_hover':   '#5BA3EC',
            'success':        '#2E7D32',
            'danger':         '#CF6679',
            'icon_bg':        '#2E3250',
            'discord':        '#5865F2',
            'github':         '#E8EAF6',
            'title_bcfd':     '#E8EAF6',
            'nav_bg':         '#1E2133',
            'nav_active':     '#FFFFFF',
            'nav_inactive':   '#7B82A8',
            'divider':        '#2E3250',
            'online':         '#2E7D32',
            'offline':        '#CF6679',
            'btn_invite':     '#5865F2',
        },
    },
    'v2_dark': {
        'swatch_a': '#0D1B2A',
        'swatch_b': '#C9A227',
        'data': {
            'bg':             '#0D1B2A',
            'card_bg':        '#12243A',
            'card_border':    '#C9A227',
            'footer_bg':      '#090F18',
            'popup_bg':       '#12243A',
            'input_bg':       '#1A2F4A',
            'input_border':   '#C9A227',
            'text':           '#E8DEB0',
            'text_dim':       '#8A7D50',
            'text_on_accent': '#0D1B2A',
            'accent':         '#C9A227',
            'accent_hover':   '#D4B040',
            'success':        '#2A8050',
            'danger':         '#A03030',
            'icon_bg':        '#1A2F4A',
            'discord':        '#5865F2',
            'github':         '#E8DEB0',
            'title_bcfd':     '#C9A227',
            'nav_bg':         '#090F18',
            'nav_active':     '#C9A227',
            'nav_inactive':   '#8A7D50',
            'divider':        '#2A3F5A',
            'online':         '#2A8050',
            'offline':        '#A03030',
            'btn_invite':     '#5865F2',
        },
    },
}

_All_THEMES = ['system_wh','system_da', 'blue_sky', 'yellow_bile']
_PKEY       = ''.join(k[0] for k in _All_THEMES)
_PLT_REF    = next((k for k in ALL_THEMES if k not in _All_THEMES), None)

def apply_theme_globally(theme_key: str):
    ThemeEngine.apply(theme_key, ALL_THEMES)

    d     = load_settings()
    patch = {'theme': theme_key}

    _prev  = d.get('theme', '')
    _depth = d.get('_ul', 0)
    _warm  = {'blue_sky', 'yellow_bile'}

    if _prev in _warm and theme_key in _warm and _prev != theme_key:
        _depth += 2
    elif theme_key in _warm:
        _depth += 1
    else:
        _depth = max(0, _depth - 1)

    patch['_ul'] = _depth
    save_settings(patch)

def _restart_app(page: ft.Page = None):
    if is_mobile():
        return

    if getattr(sys, 'frozen', False):
        try:
            subprocess.Popen([sys.executable])
        except Exception as e:
            print(f'[Settings] Relaunch failed: {e}')
    else:
        base_dir  = get_persistent_base_dir()
        fdsb_path = os.path.normpath(os.path.join(base_dir, 'FDSB.py'))
        try:
            subprocess.Popen([sys.executable, fdsb_path])
        except Exception as e:
            print(f'[Settings] Relaunch failed: {e}')

    if page is not None:
        for _attempt in (
            lambda: page.window.close(),
            lambda: page.window.destroy(),
            lambda: page.window_close(),
        ):
            try:
                _attempt()
                break
            except Exception:
                continue

    os._exit(0)

def _border_all(w: float, color: str) -> ft.Border:
    s = ft.BorderSide(w, color)
    return ft.Border(left=s, top=s, right=s, bottom=s)

def _soft_shadow(blur: int = 16, dy: int = 6, opacity: float = 0.10) -> ft.BoxShadow:
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=blur,
        color=ft.Colors.with_opacity(opacity, '#000000'),
        offset=ft.Offset(0, dy),
    )

def _card_container(content: ft.Control) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=_c('card_bg'),
        border=_border_all(1, _c('card_border')),
        border_radius=14,
        padding=ft.Padding(left=16, top=14, right=16, bottom=14),
        shadow=_soft_shadow(),
    )

def _icon_chip(icon: str, bgcolor: str = None, icon_color: str = None,
               size: int = 30) -> ft.Container:
    return ft.Container(
        content=ft.Icon(icon, size=15, color=icon_color or '#FFFFFF'),
        width=size, height=size,
        border_radius=size * 0.34,
        bgcolor=bgcolor or _c('accent'),
        alignment=ft.Alignment(0, 0),
    )


class BotSettingsTab:
    _current_view = property(lambda self: 'editor' if self._status_view else 'list')

    def __init__(self, page: ft.Page, bot_data: dict = None,
                 on_bot_save=None, on_theme_change=None, on_lang_change=None):
        self._page              = page
        self._bot_data          = bot_data or {}
        self._on_bot_save       = on_bot_save
        self._on_theme_change   = on_theme_change
        self._on_lang_change_cb = on_lang_change
        self._loading_overlay: ft.Control | None = None
        self._is_committing   = False

        self._container: ft.Container | None = None

        self._lang          = get_current_lang()
        self._current_theme = get_current_theme()
        self._theme_btns: dict[str, ft.FilledButton] = {}
        self._ext_ui_active = _ui_profile_fixed()

        self._export_status_text = ft.Text('', size=11, color=_c('success'))
        self._export_file_picker = ft.FilePicker()

        self._captcha_code    = ''
        self._captcha_display = ft.Text(
            '', size=26, weight=ft.FontWeight.BOLD,
            color=_c('text'), selectable=False,
        )
        self._captcha_field = ft.TextField(
            hint_text=_t('captcha_enter'),
            dense=True, max_length=3,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=_c('card_border'),
            focused_border_color=_c('danger'),
            cursor_color=_c('danger'),
            border_radius=10,
            text_style=ft.TextStyle(color=_c('text'), size=13),
        )
        self._captcha_section = ft.Column([], spacing=8, visible=False)

        self._delete_init_btn = ft.FilledButton(
            content=ft.Row(
                [ft.Icon(ft.Icons.DELETE_FOREVER, color='#FFFFFF'),
                 ft.Text(_t('delete_bot_perm'), color='#FFFFFF',
                         weight=ft.FontWeight.BOLD)],
                spacing=6, tight=True,
            ),
            on_click=self._show_captcha,
            style=ft.ButtonStyle(bgcolor=_c('danger'), color='#FFFFFF'),
        )

        self._name_field = ft.TextField(
            label=_t('bot_name_hint'),
            dense=True,
            prefix_icon=ft.Icons.SMART_TOY_OUTLINED,
            border_color=_c('card_border'),
            focused_border_color=_c('accent'),
            cursor_color=_c('accent'),
            border_radius=10,
            label_style=ft.TextStyle(color=_c('text_dim'), size=12),
            text_style=ft.TextStyle(color=_c('text'), size=13),
            bgcolor=_c('card_bg'),
        )
        self._token_field = ft.TextField(
            label=_t('bot_token_hint'),
            dense=True,
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.VPN_KEY_OUTLINED,
            border_color=_c('card_border'),
            focused_border_color=_c('accent'),
            cursor_color=_c('accent'),
            border_radius=10,
            label_style=ft.TextStyle(color=_c('text_dim'), size=12),
            text_style=ft.TextStyle(color=_c('text'), size=13),
            bgcolor=_c('card_bg'),
        )

        self._design_col = ft.Column(spacing=4)
        self._root_col: ft.Column = None
        self._status_view: BotStatusView | None = None
        
    async def _open_link(self, url: str):
        await self._page.launch_url(url)

    def handle_back(self) -> bool:
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
        if self._export_file_picker not in self._page.services:
            self._page.services.append(self._export_file_picker)
            self._page.update()

        self._root_col = ft.Column(
            [
                ft.Column(
                    [
                        self._build_general_section(),
                        self._build_status_bot_section(),
                        self._build_export_section(),
                        self._build_design_section(),
                        self._build_info_section(),
                        self._build_delete_section(),
                        ft.Container(height=16),
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
            self._build_design_section(),
            self._build_info_section(),
            self._build_delete_section(),
            ft.Container(height=16),
        ]
        self._page.update()

    def _build_general_section(self) -> ft.Control:
        lang_btn = self._build_lang_button()

        return ft.Column(
            [
                self._section_title(_t('general_section'), ft.Icons.TUNE_ROUNDED),
                _card_container(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        _t('language'),
                                        size=13,
                                        color=_c('text'),
                                        expand=True,
                                        weight=ft.FontWeight.W_500,
                                    ),
                                    lang_btn,
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Divider(color=_c('divider'), height=1),
                            self._name_field,
                            self._token_field,
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
                        spacing=12,
                    ),
                ),
            ],
            spacing=8,
        )

    def _build_lang_button(self) -> ft.Control:
        info = _LANG_DETAILS.get(self._lang, {'name': self._lang.upper(), 'sub': '', 'code': self._lang.upper()})

        code_badge = ft.Container(
            content=ft.Text(
                info['code'],
                size=11,
                weight=ft.FontWeight.BOLD,
                color=_c('accent'),
            ),
            bgcolor=_c('accent') + '22',
            border_radius=6,
            padding=ft.Padding(left=6, top=2, right=6, bottom=2),
        )

        return ft.Container(
            content=ft.Row(
                [
                    _icon_chip(ft.Icons.TRANSLATE_ROUNDED, bgcolor=_c('bg'), icon_color=_c('accent'), size=24),
                    ft.Text(info['name'], size=13, weight=ft.FontWeight.BOLD, color=_c('text')),
                    code_badge,
                    ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=18, color=_c('text_dim')),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=_c('input_bg'),
            border=_border_all(1, _c('input_border')),
            border_radius=10,
            padding=ft.Padding(left=10, top=6, right=8, bottom=6),
            ink=True,
            on_click=lambda _: self._open_lang_modal(),
        )

    def _open_lang_modal(self):
        available_codes = list(Translations.translations.keys())
        languages_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

        def _select_lang(code: str):
            self._page.pop_dialog()
            self._page.run_task(self._apply_language, code)

        def _populate_languages(filter_query: str = ''):
            languages_col.controls.clear()
            q = filter_query.strip().lower()

            for code in available_codes:
                info = _LANG_DETAILS.get(code, {'name': code.upper(), 'sub': code, 'code': code.upper()})
                name = info['name']
                sub  = info.get('sub', '')

                if q and (q not in name.lower() and q not in sub.lower() and q not in code.lower()):
                    continue

                is_active = (code == self._lang)

                code_badge = ft.Container(
                    content=ft.Text(
                        info['code'],
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=_c('accent') if is_active else _c('text_dim'),
                    ),
                    bgcolor=_c('accent') + '22' if is_active else _c('card_border'),
                    border_radius=6,
                    padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                )

                trailing_icon = ft.Icon(
                    ft.Icons.CHECK_CIRCLE_ROUNDED if is_active else ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED,
                    size=18,
                    color=_c('accent') if is_active else _c('card_border'),
                )

                row = ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Row([ft.Text(name, size=13, weight=ft.FontWeight.BOLD, color=_c('text')), code_badge], spacing=6),
                                    ft.Text(sub, size=11, color=_c('text_dim')) if sub else ft.Container(),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            trailing_icon,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=_c('accent') + '15' if is_active else _c('card_bg'),
                    border=_border_all(1, _c('accent') if is_active else _c('card_border')),
                    border_radius=10,
                    padding=ft.Padding(left=12, top=10, right=12, bottom=10),
                    ink=True,
                    on_click=lambda _, c=code: _select_lang(c),
                )
                languages_col.controls.append(row)

            if not languages_col.controls:
                languages_col.controls.append(
                    ft.Container(
                        content=ft.Text('No languages found', color=_c('text_dim'), size=12),
                        alignment=ft.Alignment(0, 0),
                        padding=20,
                    )
                )

        _populate_languages()

        search_field = ft.TextField(
            hint_text=_t('search_lang'),
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            dense=True,
            border_color=_c('card_border'),
            focused_border_color=_c('accent'),
            cursor_color=_c('accent'),
            text_style=ft.TextStyle(color=_c('text'), size=13),
            bgcolor=_c('input_bg'),
            border_radius=10,
            content_padding=ft.Padding(left=8, right=8, top=0, bottom=0),
            on_change=lambda e: (_populate_languages(e.control.value), self._page.update()),
        )

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=_c('popup_bg'),
            shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row(
                [
                    _icon_chip(ft.Icons.LANGUAGE_ROUNDED, bgcolor=_c('bg'), icon_color=_c('accent'), size=28),
                    ft.Text(_t('select_language'), weight=ft.FontWeight.BOLD, size=15, color=_c('text')),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        search_field,
                        ft.Container(
                            content=languages_col,
                            expand=True,
                            padding=ft.Padding(top=6, bottom=0, left=0, right=0),
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
                width=380,
                height=420,
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text(_t('cancel'), color=_c('text_dim')),
                    on_click=lambda _: self._page.pop_dialog(),
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._page.show_dialog(dlg)

    async def _apply_language(self, selected: str):
        if not selected or selected == self._lang:
            return
        save_settings({'lang': selected})
        self._lang = selected

        async def _apply(ls: LoadingScreen):
            ls.set_progress(0.3, _t('language'))
            if self._on_lang_change_cb:
                self._on_lang_change_cb(selected)
                ls.set_progress(0.7, _t('language'))
            elif self._on_theme_change:
                self._on_theme_change(self._current_theme)
                ls.set_progress(0.7, _t('language'))
            else:
                self._rebuild_in_place()
                ls.set_progress(0.7, _t('language'))
            ls.set_progress(1.0, _t('language'))

        ls = LoadingScreen(page=self._page, title=_t('language'))
        await ls.run_overlay(_apply)

    def _show_loading(self, message: str = 'Applying changes…'):
        if self._loading_overlay is not None:
            return
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
                                    self._export_status_text,
                                ],
                                spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=10,
                    ),
                ),
            ],
            spacing=8,
        )

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

    def _build_design_section(self) -> ft.Control:
        visible = list(_All_THEMES)
        if self._ext_ui_active and _PLT_REF:
            visible.append(_PLT_REF)

        self._design_col.controls.clear()
        for key in visible:
            self._design_col.controls.append(self._theme_row(key))

        return ft.Column(
            [
                self._section_title(_t('design_section'), ft.Icons.PALETTE_OUTLINED),
                _card_container(self._design_col),
            ],
            spacing=8,
        )

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

    def _build_delete_section(self) -> ft.Control:
        self._captcha_section = ft.Column(
            [
                ft.Container(
                    content=ft.Column([self._captcha_display], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=_c('card_bg'),
                    border=_border_all(2, _c('danger')),
                    border_radius=8,
                    padding=ft.Padding(left=10, top=10, right=10, bottom=10),
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Text(_t('captcha_hint'), size=12, color=_c('text_dim')),
                self._captcha_field,
                ft.FilledButton(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.WARNING_ROUNDED, color='#FFFFFF'),
                         ft.Text(_t('confirm_delete'), color='#FFFFFF', weight=ft.FontWeight.BOLD)],
                        spacing=6, tight=True,
                    ),
                    on_click=self._execute_deletion,
                    expand=True,
                    style=ft.ButtonStyle(bgcolor='#991B1B', color='#FFFFFF', shape=ft.RoundedRectangleBorder(radius=10)),
                ),
            ],
            spacing=10,
            visible=False,
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
                    content=ft.Column([self._delete_init_btn, self._captcha_section], spacing=10),
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

    def _theme_row(self, theme_key: str) -> ft.Control:
        info   = ALL_THEMES[theme_key]
        is_sel = theme_key == self._current_theme

        swatches = [info['swatch_a'], info['swatch_b']]
        if 'swatch_c' in info:
            swatches.extend([info['swatch_c'], info.get('swatch_d', info['swatch_b'])])

        swatch_widgets = [
            ft.Container(
                width=18, height=34,
                bgcolor=col,
                border_radius=ft.BorderRadius(
                    top_left=8    if i == 0                  else 0,
                    bottom_left=8 if i == 0                  else 0,
                    top_right=8   if i == len(swatches) - 1 else 0,
                    bottom_right=8 if i == len(swatches) - 1 else 0,
                ),
            )
            for i, col in enumerate(swatches)
        ]

        swatch = ft.Container(
            content=ft.Row(swatch_widgets, spacing=0),
            border=_border_all(1, _c('card_border')),
            border_radius=10,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            width=18 * len(swatches),
            height=34,
            shadow=_soft_shadow(blur=8, dy=3, opacity=0.14),
        )

        sel_btn = ft.FilledButton(
            content=ft.Text(
                '✓' if is_sel else '>',
                color='#FFFFFF' if is_sel else _c('text_dim'),
                weight=ft.FontWeight.BOLD,
            ),
            on_click=lambda _, k=theme_key: self._page.run_task(self._select_theme, k),
            style=ft.ButtonStyle(
                bgcolor=_c('accent') if is_sel else _c('card_border'),
                color='#FFFFFF',
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding(left=12, top=4, right=12, bottom=4),
            ),
        )
        self._theme_btns[theme_key] = sel_btn

        return ft.Container(
            content=ft.Row(
                [
                    swatch,
                    ft.Text(
                        _t(theme_key),
                        size=13,
                        color=_c('text'),
                        weight=ft.FontWeight.W_500,
                        expand=True,
                    ),
                    sel_btn,
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=56,
            border_radius=12,
            bgcolor=_c('accent') + '18' if is_sel else 'transparent',
            border=_border_all(1, _c('accent')) if is_sel else None,
            padding=ft.Padding(left=8, right=8, top=0, bottom=0),
            ink=True,
            on_click=lambda _, k=theme_key: self._page.run_task(self._select_theme, k),
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

    async def _select_theme(self, theme_key: str):
        if self._is_committing:
            return
        await self._commit_theme(theme_key)

    async def _commit_theme(self, theme_key: str):
        if self._is_committing:
            return
        self._is_committing = True

        try:
            async def _apply(ls: LoadingScreen):
                ls.set_progress(0.3, _t('design_section'))

                apply_theme_globally(theme_key)
                self._current_theme  = theme_key
                self._page.bgcolor   = _c('bg')

                self._page.theme_mode = (
                    ft.ThemeMode.DARK if theme_key in ('system_da', 'v2_dark')
                    else ft.ThemeMode.LIGHT
                )

                if _ui_profile_fixed() and not self._ext_ui_active:
                    self._ext_ui_active = True

                ls.set_progress(0.6, _t('design_section'))

                if self._on_theme_change:
                    self._on_theme_change(theme_key)
                else:
                    for key, btn in self._theme_btns.items():
                        active = key == theme_key
                        btn.content = ft.Text(
                            '✓' if active else '>',
                            color='#FFFFFF' if active else _c('text_dim'),
                            weight=ft.FontWeight.BOLD,
                        )
                        btn.style = ft.ButtonStyle(
                            bgcolor=_c('accent') if active else _c('card_border'),
                            color='#FFFFFF',
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.Padding(left=12, top=4, right=12, bottom=4),
                        )

                ls.set_progress(1.0, _t('design_section'))

            ls = LoadingScreen(page=self._page, title=_t('design_section'))
            await ls.run_overlay(_apply)
        finally:
            self._is_committing = False

    async def _export_bot_data(self, _):
        bot_name = self._bot_data.get('name', '').strip()
        bot_dir  = self._bot_data.get('bot_dir', '').strip()

        if not bot_name or not bot_dir:
            self._export_status_text.color = _c('danger')
            self._export_status_text.value = _t('no_bot_selected')
            self._page.update()
            return

        base_dir   = get_persistent_base_dir()
        export_dir = os.path.normpath(os.path.join(base_dir, 'app_data', 'exports'))
        os.makedirs(export_dir, exist_ok=True)

        zip_name = f'{bot_name}_export.zip'
        zip_path = os.path.join(export_dir, zip_name)

        sources = {}
        for folder in ['bot_commands', 'bot_vars']:
            candidate = os.path.normpath(
                os.path.join(base_dir, 'app_data', bot_name, folder)
            )
            if not os.path.isdir(candidate):
                candidate = os.path.normpath(os.path.join(bot_dir, folder))
            if os.path.isdir(candidate):
                sources[folder] = candidate

        if not sources:
            self._export_status_text.color = _c('danger')
            self._export_status_text.value = _t('folders_not_found')
            self._page.update()
            return

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for folder_name, folder_path in sources.items():
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            abs_p = os.path.join(root, file)
                            arc   = os.path.join(
                                folder_name, os.path.relpath(abs_p, folder_path)
                            )
                            zf.write(abs_p, arc)
        except Exception as e:
            print(f'[Settings] Export failed: {e}')
            self._export_status_text.color = _c('danger')
            self._export_status_text.value = _t('export_failed')
            self._page.update()
            return

        try:
            if is_mobile():
                saved_path = await self._export_file_picker.save_file(
                    file_name=zip_name,
                    allowed_extensions=['zip'],
                )
                if saved_path and os.path.normpath(saved_path) != os.path.normpath(zip_path):
                    shutil.copy2(zip_path, saved_path)
            else:
                if sys.platform == 'win32':
                    subprocess.Popen(['explorer', '/select,', zip_path])
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', '-R', zip_path])
                else:
                    subprocess.Popen(['xdg-open', export_dir])
        except Exception as e:
            print(f'[Settings] reveal/save failed: {e}')

        self._export_status_text.color = _c('success')
        self._export_status_text.value = _t('export_success')
        self._page.update()

    def _show_captcha(self, _):
        self._captcha_code             = ''.join(random.choices('0123456789', k=3))
        self._captcha_display.value    = self._captcha_code
        self._captcha_field.value      = ''
        self._captcha_field.error_text = None
        self._captcha_section.visible  = True
        self._delete_init_btn.visible  = False
        self._page.update()

    def _execute_deletion(self, _):
        if (self._captcha_field.value or '').strip() != self._captcha_code:
            self._captcha_code          = ''.join(random.choices('0123456789', k=3))
            self._captcha_display.value = self._captcha_code
            self._captcha_field.value   = ''
            self._captcha_field.error_text = _t('captcha_wrong')
            self._page.update()
            return

        base_dir = get_persistent_base_dir()
        bot_name = self._bot_data.get('name', '')

        if bot_name:
            target = os.path.normpath(os.path.join(base_dir, 'app_data', bot_name))
            if os.path.exists(target):
                try:
                    shutil.rmtree(target)
                    print(f'[Settings] Deleted: {target}')
                except Exception as e:
                    print(f'[Settings] Delete failed: {e}')

        if self._on_bot_save:
            self._on_bot_save({})

        if is_mobile():
            self._rebuild_in_place()
            return

        _restart_app(self._page)

    async def _save_bot(self, _):
        new_name  = (self._name_field.value or '').strip()
        new_token = (self._token_field.value or '').strip()

        if not new_token:
            self._token_field.error_text = _t('token_required')
            self._notify(_t('token_required'), _c('danger'))
            self._page.update()
            return

        # فحص أمان التوكن ومنع السيلف بوت وتوكنات الحسابات الشخصية
        old_token = self._bot_data.get('token', '').strip()
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
                cfg['name']  = new_name or cfg.get('name', 'Bot')
                cfg['token'] = new_token
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                self._bot_data.update({'name': cfg['name'], 'token': new_token})
            except Exception as e:
                print(f'[Settings] save failed: {e}')
                self._notify(f"Save error: {e}", _c('danger'))
                self._page.update()
                return

        if self._on_bot_save:
            self._on_bot_save(self._bot_data)

        self._notify(_t('saved_successfully'), _c('success'))
        self._page.update()

    def load_bot(self, bot_data: dict):
        self._bot_data          = bot_data
        self._name_field.value  = bot_data.get('name',  '')
        self._token_field.value = bot_data.get('token', '')