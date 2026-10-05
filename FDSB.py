# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# FDSB.py (root) . Flet 0.85.2+ / v1 API

import os
import re
import sys
import json
import shutil
import logging
import asyncio
import time
import zipfile 

import flet as ft

# ══════════════════════════════════════════════════════════════════════════════
#  PLATFORM DETECTION 
# ══════════════════════════════════════════════════════════════════════════════

def get_platform() -> str:
    env = os.getenv('FLET_PLATFORM', '').lower()
    if env in ('android', 'ios', 'windows', 'macos', 'linux', 'web'):
        return env
    if sys.platform.startswith('win'):
        return 'windows'
    if sys.platform.startswith('darwin'):
        return 'macos'
    if sys.platform.startswith('linux'):
        return 'linux'
    return 'unknown'


def is_mobile() -> bool:
    return get_platform() in ('android', 'ios')


def is_desktop() -> bool:
    return get_platform() in ('windows', 'macos', 'linux')


# ══════════════════════════════════════════════════════════════════════════════
#  WINDOW CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

def _configure_window(page: ft.Page):
    platform = get_platform()

    if platform == 'windows':
        page.window.width  = 1350
        page.window.height = 700

    elif platform in ('macos', 'linux'):
        page.window.width      = 420
        page.window.height     = 720
        page.window.min_width  = 360
        page.window.min_height = 600
        page.window.resizable  = False

    elif platform in ('android', 'ios'):
        page.padding = 0 

    elif platform == 'web':
        page.padding = 0

    else:
        page.window.width  = 420
        page.window.height = 720


# ══════════════════════════════════════════════════════════════════════════════
#  PERSISTENT STORAGE PATHS
# ══════════════════════════════════════════════════════════════════════════════

def get_persistent_base_dir() -> str:
    storage_data = os.getenv('FLET_APP_STORAGE_DATA')
    if storage_data:
        return storage_data
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_app_data_dir() -> str:
    path = os.path.join(get_persistent_base_dir(), 'app_data')
    os.makedirs(path, exist_ok=True)
    return path


def _server_running() -> bool:
    """Safe wrapper: if the state is unknown, assume RUNNING so nothing is deleted."""
    fn = getattr(Server, 'is_running', None)
    if not callable(fn):
        print('[FDSB] Server.is_running missing - update Server.py and fgs_service.py')
        return True
    try:
        return bool(fn())
    except Exception as ex:
        print(f'[FDSB] Server.is_running failed: {ex}')
        return True


def clear_app_cache():
    """Deletes disposable cache only. Never touches persistent data (app_data)."""
    protected = os.path.abspath(get_persistent_base_dir())
    cache_dir = os.getenv('FLET_APP_STORAGE_TEMP')
    if not cache_dir:
        return
    cache_dir = os.path.abspath(cache_dir)
    if (not os.path.isdir(cache_dir) or cache_dir == protected
            or protected.startswith(cache_dir + os.sep)):
        return
    for e in os.scandir(cache_dir):
        try:
            if e.is_dir(follow_symlinks=False):
                shutil.rmtree(e.path)
            else:
                os.remove(e.path)
        except Exception as ex:
            print(f'[Cache] could not remove {e.path}: {ex}')


def get_resource_path(*parts: str) -> str:
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


from main_app.langs.translations import Translations
from main_app.settings import get_current_lang, get_current_theme, apply_theme_globally, ALL_THEMES
from main_app.theme.theme_engine import ThemeEngine
from main_app.main import BotDashboardScreen
from main_app.load.motion import SlideStack
from main_app.load.updater import check_for_updates
from main_app.load.token_vault import TokenVault

logging.getLogger('discord').setLevel(logging.INFO)

from main_app.core_fdsb import Server

icon_path = get_resource_path('main_app', 'icons', 'FDSB.png')

# ══════════════════════════════════════════════════════════════════════════════
#  TRANSLATION HELPER
# ══════════════════════════════════════════════════════════════════════════════

def _t(key: str) -> str:
    return Translations.get(key, get_current_lang())


def _tr(key: str, ar: str, en: str) -> str:
    """Translation with inline fallback when the key is missing from translations."""
    try:
        val = Translations.get(key, get_current_lang())
        if val and val != key:
            return val
    except Exception:
        pass
    return ar if str(get_current_lang()).startswith('ar') else en

def _ar(text: str) -> str:
    return text

# ══════════════════════════════════════════════════════════════════════════════
#  STORAGE
# ══════════════════════════════════════════════════════════════════════════════

APP_DATA_DIR = get_app_data_dir()


def ensure_app_data_dir():
    os.makedirs(APP_DATA_DIR, exist_ok=True)


COUNTER_FILE = os.path.join(APP_DATA_DIR, 'counter.json')


def get_bot_dir(bot_name: str) -> str:
    """Legacy: folder derived from the name (only for bots made before IDs)."""
    safe = "".join(c for c in bot_name if c.isalnum() or c in (' ', '-', '_')).strip()
    return os.path.join(APP_DATA_DIR, safe.replace(' ', '_') or 'bot')


def get_bot_dir_by_id(bot_id: int) -> str:
    return os.path.join(APP_DATA_DIR, f'bot_{int(bot_id):04d}')


def _next_bot_number() -> int:
    """Ever-increasing bot number. Never decreases, even if bots are deleted."""
    ensure_app_data_dir()
    last = 0
    try:
        with open(COUNTER_FILE, 'r', encoding='utf-8') as f:
            last = int(json.load(f).get('last_id', 0))
    except Exception:
        last = 0
    for e in os.scandir(APP_DATA_DIR):
        m = re.fullmatch(r'bot_(\d+)', e.name)
        if e.is_dir() and m:
            last = max(last, int(m.group(1)))
    n = last + 1
    tmp = COUNTER_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'last_id': n}, f)
    os.replace(tmp, COUNTER_FILE)
    return n


def rename_bot(bot_dir: str, new_name: str) -> bool:
    path = os.path.join(bot_dir, 'bot_files', 'config.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        config['name'] = new_name.strip() or config.get('name', 'My Bot')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f'[Storage] rename failed {path}: {e}')
        return False


def save_bot_data(bot_data: dict) -> dict:
    ensure_app_data_dir()
    bot_id        = _next_bot_number()
    bot_dir       = get_bot_dir_by_id(bot_id)
    bot_files_dir = os.path.join(bot_dir, 'bot_files')
    os.makedirs(bot_dir,       exist_ok=True)
    os.makedirs(bot_files_dir, exist_ok=True)

    saved_image_path = ''
    original_image   = bot_data.get('image', '')
    if original_image and os.path.isfile(original_image):
        ext  = os.path.splitext(original_image)[1]
        dest = os.path.join(bot_dir, f'avatar{ext}')
        shutil.copy2(original_image, dest)
        saved_image_path = dest

    config = {
        'id':            bot_id,
        'name':          bot_data.get('name', 'My Bot'),
        'image':         saved_image_path,
        'token_storage': 'secure',
    }
    with open(os.path.join(bot_files_dir, 'config.json'), 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    config['_dir'] = bot_dir
    return config


def load_all_bots() -> list:
    ensure_app_data_dir()
    bots = []
    for entry in os.scandir(APP_DATA_DIR):
        if not entry.is_dir():
            continue
        config_path = os.path.join(entry.path, 'bot_files', 'config.json')
        if not os.path.isfile(config_path):
            continue
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if config.get('image') and not os.path.isfile(config['image']):
                config['image'] = ''
            config['_dir'] = entry.path
            bots.append(config)
        except Exception as e:
            print(f"[Storage] error {config_path}: {e}")
    return bots


def bot_exists(bot_name: str) -> bool:
    return os.path.isfile(
        os.path.join(get_bot_dir(bot_name), 'bot_files', 'config.json')
    )


# ══════════════════════════════════════════════════════════════════════════════
#  TOKEN VALIDATOR
# ══════════════════════════════════════════════════════════════════════════════

DISCORD_TOKEN_RE = re.compile(
    r'^[A-Za-z0-9_-]{24,28}'   
    r'\.'
    r'[A-Za-z0-9_-]{6}'        
    r'\.'
    r'[A-Za-z0-9_-]{27,38}$'   
)


def is_valid_discord_token(token: str) -> bool:
    if token == 'admin':
        return True
    return bool(DISCORD_TOKEN_RE.match(token))


def _c(key: str) -> str:
    return ThemeEngine.hex(key)


# ══════════════════════════════════════════════════════════════════════════════
#  BACK-BUTTON HANDLING
# ══════════════════════════════════════════════════════════════════════════════

_NAV_STACK: list = []  
_CURRENT_SCREEN = {'kind': None, 'dashboard': None}   


def _nav_push(back_fn):
    _NAV_STACK.append(back_fn)


def _nav_pop() -> bool:
    if _NAV_STACK:
        fn = _NAV_STACK.pop()
        fn()
        return True
    return False


def _nav_clear():
    _NAV_STACK.clear()


def _dashboard_back(dashboard) -> bool:
    """Ask the open dashboard to go back one level internally
    (editor -> commands list, sub-page -> tab root, ...).
    Returns True if something was handled.

    1. Uses dashboard.handle_back() when the dashboard defines it.
    2. Otherwise scans its attributes for any child (tab) exposing handle_back(),
       so the editor's back step works even if the dashboard does not forward it.
    """
    if dashboard is None:
        return False

    handler = getattr(dashboard, 'handle_back', None)
    if callable(handler):
        try:
            return bool(handler())
        except Exception as ex:
            print(f'[FDSB] dashboard.handle_back failed: {ex}')
            return False

    try:
        children = list(vars(dashboard).values())
    except TypeError:
        children = []
    for child in children:
        if child is dashboard or isinstance(child, (str, int, float, bool, dict, list, tuple, set)):
            continue
        child_handler = getattr(child, 'handle_back', None)
        if callable(child_handler):
            try:
                if child_handler():
                    return True
            except Exception as ex:
                print(f'[FDSB] child.handle_back failed: {ex}')
    return False


# حالة نافذة الخروج.
# على أندرويد: عند الضغط على رجوع النظام، يرسل Flet الحدث on_confirm_pop ثم ينتظر
# (حتى 5 دقائق) أن نستدعي view.confirm_pop(True/False):
#   False -> يبقى التطبيق      True -> يغلق التطبيق فعلياً (SystemNavigator.pop)
# لذلك أثناء ظهور نافذة الخروج نترك هذا الطلب "معلّقاً" ونحسمه حسب اختيار المستخدم.
_EXIT_STATE = {'dialog': None, 'view': None, 'asking': False}


async def _resolve_pop(should_pop: bool):
    view = _EXIT_STATE.get('view')
    if view is None:
        return
    try:
        await view.confirm_pop(should_pop)
    except Exception as ex:
        print(f'[FDSB] confirm_pop({should_pop}) failed: {ex}')


def _show_exit_confirm(page: ft.Page):
    """Small 'are you sure you want to exit?' dialog shown at the root screen."""
    if _EXIT_STATE['asking']:
        return                                   # لا نفتح نافذتين فوق بعض
    _EXIT_STATE['asking'] = True

    async def _stay(_=None):
        _EXIT_STATE['asking'] = False
        page.pop_dialog()
        await _resolve_pop(False)                # إلغاء الإغلاق

    async def _exit(_=None):
        _EXIT_STATE['asking'] = False
        page.pop_dialog()
        await _resolve_pop(True)                 # إغلاق التطبيق بالكامل

    async def _dismissed(_=None):
        # أُغلقت النافذة بزر الرجوع أو بالضغط خارجها = البقاء
        if _EXIT_STATE['asking']:
            _EXIT_STATE['asking'] = False
            await _resolve_pop(False)

    dlg = ft.AlertDialog(
        modal=False,                             # الرجوع مرة أخرى يغلق النافذة (= البقاء)
        title=ft.Text(
            _tr('exit_title', 'الخروج من التطبيق', 'Exit app'),
            color=_c('text'),
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        ),
        content=ft.Text(
            _tr('exit_message', 'هل أنت متأكد أنك تريد الخروج؟',
                'Are you sure you want to exit?'),
            color=_c('text'),
            text_align=ft.TextAlign.CENTER,
        ),
        actions=[
            ft.TextButton(
                content=ft.Text(_tr('exit_stay', 'البقاء', 'Stay'), color=_c('text')),
                on_click=_stay,
            ),
            ft.TextButton(
                content=ft.Text(_tr('exit_confirm', 'خروج', 'Exit'), color=_c('danger')),
                on_click=_exit,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
        bgcolor=_c('popup_bg'),
        shape=ft.RoundedRectangleBorder(radius=16),
        on_dismiss=_dismissed,
    )
    _EXIT_STATE['dialog'] = dlg
    page.show_dialog(dlg)


def _perform_back(page: ft.Page = None, ask_exit: bool = True) -> bool:
    """One 'back' step, deepest level first:

        dialog  ->  editor (inside dashboard)  ->  commands/tabs  ->  bot list  ->  exit prompt

    Always returns True: the app never closes by itself, we either navigate
    one level back or ask the user to confirm exit.
    """
    try:
        # 0. نافذة حوارية مفتوحة؟ أغلقها فقط. (pop_dialog لا يرمي خطأ عند عدم وجود نافذة
        #    بل يرجع None، لذلك يجب فحص القيمة المرجعة وإلا يُعتبر الرجوع "تم" دائماً.)
        if page is not None and page.pop_dialog() is not None:
            return True

        # 1. داخل لوحة تحكم البوت: دع المحرر/التبويب يعالج الرجوع أولاً
        if _CURRENT_SCREEN.get('kind') == 'dashboard':
            if _dashboard_back(_CURRENT_SCREEN.get('dashboard')):
                return True

        # 2. الرجوع للشاشة السابقة (لوحة التحكم -> واجهة البوتات)
        if _nav_pop():
            return True

        # 3. نحن في الواجهة الرئيسية: اسأل المستخدم عن الخروج
        if page is not None and ask_exit:
            _show_exit_confirm(page)
        return True
    except Exception as ex:
        print(f'[FDSB] back failed: {ex}')
        return True


_ROOT = {'stack': None, 'prev_kind': None}


def _root_stack(page: ft.Page) -> SlideStack:
    if _ROOT['stack'] is None:
        _ROOT['stack'] = SlideStack(page)
    return _ROOT['stack']


def _set_body(page: ft.Page, content: ft.Control):
    body = ft.SafeArea(content=content, expand=True) if is_mobile() else content

    body.key = f"screen_{_CURRENT_SCREEN['kind']}_{time.time()}"

    root = _root_stack(page)
    prev, kind = _ROOT['prev_kind'], _CURRENT_SCREEN['kind']
    _ROOT['prev_kind'] = kind
    if prev == 'main' and kind == 'dashboard':
        direction = 1         # dashboard slides in from the right
    elif prev == 'dashboard' and kind == 'main':
        direction = -1        # bot list slides back in from the left
    else:
        direction = 0         # first screen / same screen

    async def _handle_view_pop(e):
        # يصل هنا كل ضغطة على زر الرجوع في أندرويد.
        view = page.views[0] if page.views else None
        _EXIT_STATE['view'] = view
        _perform_back(page)
        # إن تمّ التنقل داخلياً نلغي الإغلاق فوراً. أما إن ظهرت نافذة الخروج
        # فنترك الطلب معلّقاً ليحسمه زر "خروج" أو "البقاء".
        if not _EXIT_STATE['asking'] and view is not None:
            try:
                await view.confirm_pop(False)
            except Exception:
                pass

    if not page.views:
        page.views.append(
            ft.View(
                route='/',
                controls=[root.control],
                padding=0,
                can_pop=False,
                on_confirm_pop=_handle_view_pop,
            )
        )
    else:
        if page.views[0].controls != [root.control]:
            page.views[0].controls = [root.control]
        page.views[0].can_pop = False
        page.views[0].on_confirm_pop = _handle_view_pop

    root.show(body, direction, push=False)
    page.update()


# ══════════════════════════════════════════════════════════════════════════════
#  WARNING DIALOG
# ══════════════════════════════════════════════════════════════════════════════

def _show_warning(page: ft.Page, message: str):
    def _close(_):
        page.pop_dialog()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(
            '!',
            color=_c('danger'),
            size=28,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        ),
        content=ft.Text(
            message,
            color=_c('text'),
            text_align=ft.TextAlign.CENTER,
        ),
        actions=[
            ft.TextButton(
                content=ft.Text(_t('ok'), color=_c('danger')),
                on_click=_close,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
        bgcolor=_c('popup_bg'),
        shape=ft.RoundedRectangleBorder(radius=16),
    )
    page.show_dialog(dlg)


# ══════════════════════════════════════════════════════════════════════════════
#  BOT CARD
# ══════════════════════════════════════════════════════════════════════════════

def build_bot_card(
    bot_data: dict,
    on_open_dashboard,
) -> ft.Container:

    img_path = bot_data.get('image', '')
    if img_path and os.path.isfile(img_path):
        avatar = ft.Image(
            src=img_path,
            width=42, height=42,
            fit=ft.BoxFit.COVER,
            border_radius=21,
        )
    else:
        avatar = ft.Container(
            content=ft.Text(_t('avatar_none'), size=11, color=_c('text_dim')),
            width=42, height=42,
            border_radius=21,
            bgcolor=_c('icon_bg'),
            alignment=ft.Alignment(0, 0),
        )

    name_lbl = ft.Text(
        bot_data.get('name', 'Bot'),
        size=14,
        weight=ft.FontWeight.BOLD,
        color=_c('text'),
    )

    go_btn = ft.IconButton(
        icon=ft.Icons.ARROW_FORWARD_ROUNDED,
        icon_color=_c('text_on_accent'),
        bgcolor=_c('accent'),
        icon_size=18,
        on_click=lambda _: on_open_dashboard(bot_data),
        tooltip='Open Dashboard',
        style=ft.ButtonStyle(shape=ft.CircleBorder()),
    )

    return ft.Container(
        content=ft.Row(
            [avatar, ft.Column([name_lbl], expand=True), go_btn],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        padding=ft.Padding(left=14, top=10, right=14, bottom=10),
        height=70,
        bgcolor=_c('card_bg'),
        border_radius=12,
        border=ft.Border(
            left=ft.BorderSide(1, _c('card_border')),
            top=ft.BorderSide(1, _c('card_border')),
            right=ft.BorderSide(1, _c('card_border')),
            bottom=ft.BorderSide(1, _c('card_border')),
        ),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CREATE BOT DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class CreateBotDialog:

    def __init__(self, page: ft.Page, on_create: callable):
        self._page      = page
        self._on_create = on_create
        self._img_path  = ''

        self._avatar_stack = ft.Stack(
            [
                ft.Container(
                    content=ft.Text(
                        _t('image_label'),
                        size=12,
                        color=_c('text'),
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=80, height=80,
                    bgcolor=_c('icon_bg'),
                    border_radius=40,
                    alignment=ft.Alignment(0, 0),
                )
            ],
            width=80, height=80,
        )
        self._pick_btn = ft.TextButton(
            content=ft.Row(
                [ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED, color=_c('accent')),
                 ft.Text(_t('image_label'), color=_c('accent'))],
                spacing=4, tight=True,
            ),
            on_click=self._pick_image,
        )

        self._name_field = ft.TextField(
            label=_t('name_label') or 'Bot Name',
            hint_text=_t('name_hint') or 'My Awesome Bot',
            border_color=_c('input_border'),
            focused_border_color=_c('accent'),
            cursor_color=_c('accent'),
            bgcolor=_c('input_bg'),
            border_radius=10,
            label_style=ft.TextStyle(color=_c('text'), size=13),
            text_style=ft.TextStyle(color=_c('text'), size=13),
            hint_style=ft.TextStyle(color=_c('text_dim'), size=13),
            on_change=lambda e: self._refresh_import_availability(),
        )
        self._token_field = ft.TextField(
            label=_t('token_label') or 'Bot Token',
            hint_text=_t('token_hint') or 'Paste your Discord token here',
            password=True,
            can_reveal_password=True,
            border_color=_c('input_border'),
            focused_border_color=_c('accent'),
            cursor_color=_c('accent'),
            bgcolor=_c('input_bg'),
            border_radius=10,
            label_style=ft.TextStyle(color=_c('text'), size=13),
            text_style=ft.TextStyle(color=_c('text'), size=13),
            hint_style=ft.TextStyle(color=_c('text_dim'), size=13),
            on_change=lambda e: self._refresh_import_availability(),
        )

        self._file_picker = ft.FilePicker()
        self._import_zip_path    = ''
        self._import_file_picker = ft.FilePicker()
        self._import_status_text = ft.Text('', size=11)
        self._import_btn = ft.OutlinedButton(
            content=ft.Row(
                [ft.Icon(ft.Icons.UNARCHIVE_OUTLINED, size=16, color=_c('accent')),
                 ft.Text(_t('import_zip_btn'), size=13, color=_c('accent'))],
                spacing=6, tight=True,
            ),
            on_click=self._pick_import_zip,
            disabled=True,
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, _c('accent')),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding(left=12, top=8, right=12, bottom=8),
            ),
        )
        self._import_clear_btn = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_size=16,
            icon_color=_c('danger'),
            visible=False,
            tooltip=_t('import_zip_clear'),
            on_click=self._clear_import_zip,
        )
        self._refresh_import_availability()

        self._dlg = ft.AlertDialog(
            modal=True,
            bgcolor=_c('popup_bg'),
            shape=ft.RoundedRectangleBorder(radius=18),
            title=ft.Text(
                _t('new_bot'),
                weight=ft.FontWeight.BOLD,
                color=_c('text'),
            ),
            content=ft.Column(
                [
                    ft.Row(
                        [self._avatar_stack, self._pick_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                    ),
                    self._name_field,
                    self._token_field,
                    ft.Row(
                        [self._import_btn, self._import_clear_btn],
                        spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self._import_status_text,
                ],
                tight=True,
                spacing=14,
                width=300,
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text('Cancel', color=_c('text_dim')),
                    on_click=self._cancel,
                ),
                ft.FilledButton(
                    content=ft.Text(_t('make') or 'Create', color='#FFFFFF', weight=ft.FontWeight.W_600),
                    on_click=self._submit,
                    style=ft.ButtonStyle(
                        bgcolor=_c('accent'),
                        color='#FFFFFF',
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.Padding(left=20, top=10, right=20, bottom=10),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def open(self):
        self._page.show_dialog(self._dlg)

    async def _pick_image(self, _):
        files = await self._file_picker.pick_files(
            dialog_title='Choose Bot Image',
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=['png', 'jpg', 'jpeg', 'gif', 'webp'],
        )
        if not files:
            return
        path = files[0].path
        if not path or not os.path.isfile(path):
            return

        self._img_path = path
        self._avatar_stack.controls.clear()
        self._avatar_stack.controls.append(
            ft.Container(
                content=ft.Image(
                    src=path,
                    width=80, height=80,
                    fit=ft.BoxFit.COVER,
                    border_radius=40,
                ),
                width=80, height=80,
                border_radius=40,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            )
        )
        self._page.update()

    def _refresh_import_availability(self):
        name_ok  = bool((self._name_field.value or '').strip())
        token    = (self._token_field.value or '').strip()
        token_ok = bool(token) and is_valid_discord_token(token)
        ready    = name_ok and token_ok

        self._import_btn.disabled = not ready

        if self._import_zip_path:
            pass 
        elif not ready:
            self._import_status_text.value = _t('import_zip_disabled_hint')
            self._import_status_text.color = _c('text_dim')
        else:
            self._import_status_text.value = ''

        if hasattr(self, '_dlg'):
            self._page.update()

    @staticmethod
    def _is_valid_backup_zip(path: str) -> bool:
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                names = zf.namelist()
        except Exception:
            return False
        return any(n.startswith('bot_commands/') or n.startswith('bot_vars/') for n in names)

    async def _pick_import_zip(self, _):
        if self._import_file_picker not in self._page.services:
            self._page.services.append(self._import_file_picker)

        files = await self._import_file_picker.pick_files(
            dialog_title=_t('import_zip_pick_title'),
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=['zip'],
        )
        if not files:
            return
        path = files[0].path
        if not path or not os.path.isfile(path):
            return

        if not self._is_valid_backup_zip(path):
            self._import_zip_path = ''
            self._import_clear_btn.visible = False
            self._import_status_text.value = _t('import_zip_invalid')
            self._import_status_text.color = _c('danger')
            self._page.update()
            return

        self._import_zip_path = path
        self._import_clear_btn.visible = True
        self._import_status_text.value = _t('import_zip_selected').format(
            file_name=os.path.basename(path)
        )
        self._import_status_text.color = _c('success')
        self._page.update()

    def _clear_import_zip(self, _):
        self._import_zip_path = ''
        self._import_clear_btn.visible = False
        self._refresh_import_availability()

    async def _submit(self, _):
        name  = self._name_field.value.strip() or 'My Bot'
        token = self._token_field.value.strip()

        if not token:
            self._token_field.error_text = _t('token_required')
            self._page.update()
            return

        if not is_valid_discord_token(token):
            self._token_field.error_text = (
                _t('token_invalid_format')
                or 'Invalid token format.'
            )
            self._page.update()
            return

        self._token_field.error_text = None
        self._page.pop_dialog()
        await self._on_create({
            'name': name,
            'token': token,
            'image': self._img_path,
            'import_zip': self._import_zip_path,
        })

    def _cancel(self, _):
        self._page.pop_dialog()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN VIEW
# ══════════════════════════════════════════════════════════════════════════════

class MainView:

    def __init__(self, page: ft.Page, on_open_dashboard: callable):
        self._page              = page
        self._on_open_dashboard = on_open_dashboard

        self._count_label = ft.Text(
            value="",
            size=11,
            color=_c('text_dim'),
        )

        self._cards_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

        self._empty_label = ft.Container(
            content=ft.Text(
                _t('no_bots_hint'),
                size=14,
                color=_c('text_dim'),
                text_align=ft.TextAlign.CENTER,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

        self._load_saved_bots()
        self._update_bot_count()

    def _update_bot_count(self):
        count = len(self._cards_col.controls)
        self._count_label.value = _t('total_bots_count').format(count=count)

    async def _open_link(self, url: str):
        await self._page.launch_url(url)

    def build(self) -> ft.Control:
        header = ft.Container(
            content=ft.Column(
                [
                    self._count_label,
                    ft.Text(
                        _t('main_title'),
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=_c('title_bcfd'),
                    ),
                ],
                spacing=2,
            ),
            padding=ft.Padding(left=18, top=10, right=18, bottom=10),
        )

        self._content_area = ft.Container(
            content=self._cards_col if self._cards_col.controls else self._empty_label,
            expand=True,
            padding=ft.Padding(left=16, top=8, right=16, bottom=8),
        )

        footer = ft.Container(
            content=ft.Row(
                [
                    ft.FilledButton(
                        content=ft.Row(
                            [ft.Icon(ft.Icons.TAG, color='#FFFFFF', size=16),
                             ft.Text(_t('discord'), color='#FFFFFF', size=13)],
                            spacing=5, tight=True,
                        ),
                        style=ft.ButtonStyle(
                            bgcolor=_c('discord'),
                            color='#FFFFFF',
                            shape=ft.RoundedRectangleBorder(radius=20),
                            padding=ft.Padding(left=12, top=8, right=12, bottom=8),
                        ),
                        on_click=lambda _: self._page.run_task(self._open_link, 'https://discord.gg/JngaJRC6Y9'),
                    ),
                    ft.Container(expand=True),
                    ft.FilledButton(
                        content=ft.Row(
                            [ft.Icon(ft.Icons.ADD, color='#FFFFFF', size=16),
                             ft.Text(_t('new_bot'), color='#FFFFFF', size=13)],
                            spacing=5, tight=True,
                        ),
                        style=ft.ButtonStyle(
                            bgcolor=_c('accent'),
                            color='#FFFFFF',
                            shape=ft.RoundedRectangleBorder(radius=20),
                            padding=ft.Padding(left=12, top=8, right=12, bottom=8),
                        ),
                        on_click=self._open_create_dialog,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=_c('footer_bg'),
            padding=ft.Padding(left=14, top=11, right=14, bottom=11),
            height=62,
        )

        return ft.Column(
            [header, self._content_area, footer],
            spacing=0,
            expand=True,
        )

    def _open_create_dialog(self, _):
        CreateBotDialog(self._page, on_create=self._add_bot).open()

    def _load_saved_bots(self):
        for bot_data in load_all_bots():
            self._push_card(bot_data)

    async def _add_bot(self, data: dict):
        name = data.get('name', 'My Bot')
        token = data.get('token', '')

        config  = save_bot_data(data)
        bot_dir = config['_dir']

        try:
            await TokenVault.set(TokenVault.bot_id_from_dir(bot_dir), token)
        except Exception as e:
            print(f'[MainView] secure token storage failed: {e}')
            shutil.rmtree(bot_dir, ignore_errors=True)
            _show_warning(
                self._page,
                'Could not store the token securely on this device.',
            )
            return

        import_zip = data.get('import_zip', '')
        if import_zip and os.path.isfile(import_zip):
            self._restore_bot_backup(bot_dir, import_zip)

        self._push_card(config)
        self._refresh_content_area()
        self._update_bot_count()
        self._page.update()

    @staticmethod
    def _restore_bot_backup(bot_dir: str, zip_path: str):
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for member in zf.namelist():
                    if member.startswith('bot_commands/') or member.startswith('bot_vars/'):
                        zf.extract(member, bot_dir)
        except Exception as e:
            print(f'[MainView] backup restore failed: {e}')

    def _push_card(self, bot_data: dict):
        card = build_bot_card(
            bot_data=bot_data,
            on_open_dashboard=self._on_open_dashboard,
        )
        self._cards_col.controls.append(card)

    def _refresh_content_area(self):
        if not hasattr(self, '_content_area'):
            return
        if self._cards_col.controls:
            self._content_area.content = self._cards_col
        else:
            self._content_area.content = self._empty_label


# ══════════════════════════════════════════════════════════════════════════════
#  NAVIGATION HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _dispose_current_dashboard():
    old = _CURRENT_SCREEN.get('dashboard')
    if old is not None:
        try:
            old.dispose()
        except Exception as e:
            print(f'[FDSB] dashboard dispose failed: {e}')
    _CURRENT_SCREEN['dashboard'] = None


def _show_main(page: ft.Page):
    _dispose_current_dashboard()

    def open_dashboard(bot_data: dict):
        _show_dashboard(page, bot_data)

    view = MainView(page=page, on_open_dashboard=open_dashboard)

    _CURRENT_SCREEN['kind']      = 'main'
    _CURRENT_SCREEN['dashboard'] = None
    _nav_clear()        

    _set_body(page, view.build())


def _show_dashboard(page: ft.Page, bot_data: dict):
    _dispose_current_dashboard()
    bot_dir = bot_data.get('_dir') or get_bot_dir(bot_data.get('name', 'bot'))

    dashboard = BotDashboardScreen(page=page, bot_dir=bot_dir, on_back=lambda: _show_main(page))

    _CURRENT_SCREEN['kind']      = 'dashboard'
    _CURRENT_SCREEN['dashboard'] = dashboard
    _nav_push(lambda: _show_main(page))  

    _set_body(page, dashboard.build())


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

async def main(page: ft.Page):
    page.title   = 'FDSB'
    page.padding = 0

    if is_desktop():
        page.window.icon = icon_path

    _configure_window(page)

    if not _server_running():
        clear_app_cache()

    try:
        Server.ensure_background_mode(page)
    except Exception as e:
        print(f'[FDSB] background mode failed: {e}')

    fonts_dir = get_resource_path('main_app', 'langs', 'fonts')
    fonts = {}
    if os.path.isdir(fonts_dir):
        for file in os.listdir(fonts_dir):
            if file.lower().endswith('.ttf'):
                name = os.path.splitext(file)[0]
                fonts[name] = os.path.join(fonts_dir, file)

    page.fonts = fonts
    default_font = "Cairo" if "Cairo" in fonts else next(iter(fonts), "Cairo")
    page.theme = ft.Theme(font_family=default_font)
    page.dark_theme = ft.Theme(font_family=default_font)

    saved_theme = get_current_theme() or 'system_wh'
    if saved_theme not in ALL_THEMES:
        saved_theme = 'system_wh'

    page.theme_mode = (
        ft.ThemeMode.DARK if saved_theme in ('system_da', 'v2_dark')
        else ft.ThemeMode.LIGHT
    )

    apply_theme_globally(saved_theme)

    def _sync_page_bg(data: dict):
        page.bgcolor = data.get('bg', '#FFFFFF')
        page.update()

    page._bg_sync = _sync_page_bg
    ThemeEngine.subscribe(page._bg_sync)
    page.bgcolor = ThemeEngine.hex('bg')

    migration_failed: list[str] = []
    try:
        TokenVault.attach(page)
        _, migration_failed = await TokenVault.migrate_plaintext(APP_DATA_DIR)
        await TokenVault.preload(APP_DATA_DIR)
    except Exception as e:
        print(f'[FDSB] token vault init failed: {e}')

    _show_main(page)

    if migration_failed:
        _show_warning(
            page,
            'Some bot tokens could not be moved to secure storage: '
            + ', '.join(migration_failed),
        )

    def _on_lifecycle(e: ft.AppLifecycleStateChangeEvent):
        if e.state == ft.AppLifecycleState.DETACH and not _server_running():
            clear_app_cache()

    page.on_app_lifecycle_state_change = _on_lifecycle

    def _on_key(e: ft.KeyboardEvent):
        if e.key in ('Escape', 'Back', 'Go Back'):
            _perform_back(page, ask_exit=False)

    page.on_keyboard_event = _on_key

    page.run_task(check_for_updates, page, APP_DATA_DIR, get_platform())

if __name__ == '__main__':
    ft.run(main)