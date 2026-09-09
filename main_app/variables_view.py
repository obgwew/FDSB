# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/variables_view.py . migrated to Flet 0.85.2+ / v1 API

import os
import json
import asyncio
import flet as ft

from main_app.langs.translations import Translations
from main_app.settings           import get_current_lang
from main_app.theme.theme_engine import ThemeEngine
from main_app.core_fdsb.FDCore   import set_vars_dir as _fd_set_vars_dir

def _vars_dir(bot_dir: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(bot_dir)), 'bot_vars')

def _sync_fdcore(bot_dir: str):
    path = _vars_dir(bot_dir)
    os.makedirs(path, exist_ok=True)
    _fd_set_vars_dir(path)

def _ids_data_path(bot_dir: str) -> str:
    vars_dir = _vars_dir(bot_dir)
    return os.path.join(os.path.dirname(vars_dir), 'bot_ids', 'ids_data.json')

def _load_ids_data(bot_dir: str) -> dict:
    path = _ids_data_path(bot_dir)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f'[Variables] ids_data load error {path}: {e}')
        return {}

def _save_ids_data(bot_dir: str, data: dict):
    path = _ids_data_path(bot_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

    msg_template  = _t('delete_confirm') or 'Are you sure you want to delete "{item_name}"?\nThis action cannot be undone.'
    formatted_msg = msg_template.replace('{item_name}', item_name)

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=_c('card_bg'),
        shape=ft.RoundedRectangleBorder(radius=16),
        title=ft.Row(
            [
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=_c('danger'), size=22),
                ft.Text(_t('delete_q') or 'Delete?', weight=ft.FontWeight.BOLD,
                        color=_c('text'), size=16),
            ],
            spacing=8,
        ),
        content=ft.Text(_ar(formatted_msg), color=_c('text_dim'), size=13),
        actions=[
            ft.TextButton(
                content=ft.Text(_t('cancel') or 'Cancel', color=_c('text_dim')),
                on_click=_cancel,
            ),
            ft.FilledButton(
                content=ft.Row(
                    [ft.Icon(ft.Icons.DELETE_FOREVER_ROUNDED, color='#FFFFFF', size=16),
                     ft.Text(_t('delete') or 'Delete', color='#FFFFFF',
                             weight=ft.FontWeight.BOLD)],
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
        content=ft.Text(_t('unsaved_body'), color=_c('text_dim'), size=13),
        actions=[
            ft.TextButton(
                content=ft.Text(_t('cancel') or 'Cancel', color=_c('text_dim')),
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

def _bot_root_from_dir(bot_dir: str) -> str:
    return os.path.dirname(os.path.abspath(bot_dir))

def _ensure_vars_dir(bot_dir: str) -> str:
    path = _vars_dir(bot_dir)
    os.makedirs(path, exist_ok=True)
    return path

def _var_path(bot_dir: str, name: str) -> str:
    safe = ''.join(c for c in name if c.isalnum() or c in ('-', '_')).strip() or 'var'
    return os.path.join(_vars_dir(bot_dir), f'{safe}.json')

def _var_file_exists(bot_dir: str, safe_name: str, exclude_path: str = '') -> bool:
    exclude_abs = os.path.abspath(exclude_path) if exclude_path else ''
    candidate = os.path.join(_vars_dir(bot_dir), f'{safe_name}.json')
    if os.path.isfile(candidate) and os.path.abspath(candidate) != exclude_abs:
        return True
    return False

def _load_all_vars(bot_dir: str) -> list:
    d = _vars_dir(bot_dir)
    if not os.path.isdir(d):
        return []
    result = []
    for fname in sorted(os.listdir(d)):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(d, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                data['_path'] = fpath
                result.append(data)
        except Exception as e:
            print(f'[Variables] load error {fpath}: {e}')
    return result

def _write_var(bot_dir: str, name: str, value: str, old_path: str = '') -> str:
    safe = ''.join(c for c in name if c.isalnum() or c in ('-', '_')).strip() or 'var'
    new_path = os.path.join(_vars_dir(bot_dir), f'{safe}.json')
    if old_path and os.path.abspath(old_path) != os.path.abspath(new_path):
        if os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
    _ensure_vars_dir(bot_dir)
    with open(new_path, 'w', encoding='utf-8') as f:
        json.dump({'name': name, 'value': value}, f, ensure_ascii=False, indent=2)
    print(f'[Variables] saved → {new_path}')
    return new_path

def _delete_var(path: str):
    if os.path.isfile(path):
        try:
            os.remove(path)
            print(f'[Variables] deleted → {path}')
        except Exception as e:
            print(f'[Variables] delete error: {e}')


class BotVariablesTab:

    def __init__(self, page: ft.Page):
        self._page         = page
        self._bot_dir      = ''
        self._variables    = []
        self._ids_data: dict = {}
        self._edit_path    = ''
        self._current_view = 'list'

        # العداد المخصص
        self._count_label = ft.Text(
            value="",
            size=11,
            color=_c('text_dim'),
        )

        self._is_dirty  = False
        self._snapshot: dict = {}

        self._poll_task = None
        self._json_editor_var = ''
        self._json_editor_dirty = False

        self._build_controls()
        self._build_json_editor_dialog()
        self._container = ft.Container(
            content=self._list_root,
            expand=True,
        )

        ThemeEngine.subscribe(self._on_theme)

    def handle_back(self) -> bool:
        if getattr(self, '_json_editor_dialog', None) and getattr(self._json_editor_dialog, 'open', False):
            self._request_close_json_editor(None)
            return True
        if self._current_view != 'list':
            self.guard_navigation(self._show_list)
            return True
        return False

    def build(self) -> ft.Control:
        return self._container

    def load_bot(self, bot_dir: str):
        self._bot_dir   = bot_dir
        _sync_fdcore(bot_dir)
        self._variables = _load_all_vars(bot_dir)
        self._ids_data  = _load_ids_data(bot_dir)
        self._update_vars_count()
        if self._current_view == 'list':
            self._refresh_list()
        self._start_polling()

    def _update_vars_count(self):
        count = len(self._variables)
        self._count_label.value = _t('total_vars_count').format(count=count)

    def dispose(self):
        self._stop_polling()

    def _start_polling(self):
        if self._poll_task is not None:
            return
        self._poll_task = self._page.run_task(self._poll_loop)

    def _stop_polling(self):
        if self._poll_task is not None:
            self._poll_task.cancel()
            self._poll_task = None

    async def _poll_loop(self):
        try:
            while True:
                await asyncio.sleep(2)
                if not self._bot_dir:
                    continue
                if self._current_view == 'list':
                    self._refresh_list()
        except asyncio.CancelledError:
            pass

    def _set_name_error(self):
        self._name_inp.error                = _t('enter_variable_name') or 'Name is required'
        self._name_inp.border_color         = _c('danger')
        self._name_inp.focused_border_color = _c('danger')

    def _set_name_taken_error(self):
        self._name_inp.error                = _t_or('name_taken', 'Variable name already exists')
        self._name_inp.border_color         = _c('danger')
        self._name_inp.focused_border_color = _c('danger')

    def _clear_name_error(self):
        if self._name_inp.error:
            self._name_inp.error                = None
            self._name_inp.border_color         = _c('card_border')
            self._name_inp.focused_border_color = _c('accent')

    def _mark_dirty(self, e=None):
        name_error_was_cleared = False
        if e is not None and e.control is self._name_inp and self._name_inp.error:
            self._clear_name_error()
            name_error_was_cleared = True

        scoped_visibility_changed = False
        if e is not None and e.control is self._name_inp:
            was_visible = self._scoped_btn.visible
            self._update_scoped_btn_visibility()
            scoped_visibility_changed = (self._scoped_btn.visible != was_visible)

        cur = {
            'name':  self._name_inp.value  or '',
            'value': self._value_inp.value or '',
        }
        dirty = cur != self._snapshot
        state_changed = (dirty != self._is_dirty) or scoped_visibility_changed
        if dirty != self._is_dirty:
            self._is_dirty          = dirty
            self._dirty_dot.visible = dirty

        if (state_changed or name_error_was_cleared) and self._page:
            self._page.update()

    def _clear_dirty(self):
        self._snapshot = {
            'name':  self._name_inp.value  or '',
            'value': self._value_inp.value or '',
        }
        self._is_dirty          = False
        self._dirty_dot.visible = False

    @property
    def is_dirty(self) -> bool:
        return self._current_view == 'editor' and self._is_dirty

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

    def guard_tab_change(self, on_proceed: callable, on_cancel: callable = None):
        def _reset_then_proceed():
            _sync_fdcore(self._bot_dir)
            self._variables    = _load_all_vars(self._bot_dir)
            self._current_view = 'list'
            self._update_vars_count()
            self._refresh_list()
            self._container.content = self._list_root
            on_proceed and on_proceed()

        if self.is_dirty:
            self.guard_navigation(_reset_then_proceed, on_cancel)
        else:
            _reset_then_proceed()

    def _save_then_proceed(self, on_proceed, on_cancel: callable = None):
        if self._perform_save():
            on_proceed and on_proceed()
        else:
            on_cancel and on_cancel()

    def _discard_and_proceed(self, on_proceed):
        self._clear_dirty()
        on_proceed and on_proceed()

    def _request_back(self, _):
        self.guard_navigation(self._show_list)

    def _on_theme(self, data: dict):
        g = lambda k: data.get(k, '#888888')

        self._count_label.color       = g('text_dim')
        self._search_inp.bgcolor      = g('card_bg')
        self._search_inp.border_color = g('card_border')
        self._header_title.color      = g('text')
        self._fab.bgcolor             = g('accent')
        self._fab.foreground_color    = g('text_on_accent')

        self._editor_title.color             = g('text')
        self._editor_breadcrumb.color        = g('text_dim')
        self._back_btn.bgcolor               = g('accent')
        self._back_btn.icon_color            = g('text_on_accent')
        self._dirty_dot.bgcolor              = g('warning')
        self._scoped_btn.icon_color          = g('text_dim')
        self._name_inp.bgcolor               = g('card_bg')
        self._name_inp.border_color          = g('card_border')
        self._name_inp.focused_border_color  = g('accent')
        self._name_inp.cursor_color          = g('accent')
        self._value_inp.bgcolor              = g('card_bg')
        self._value_inp.border_color         = g('card_border')
        self._value_inp.focused_border_color = g('accent')
        self._value_inp.cursor_color         = g('accent')
        self._save_btn.style                 = _btn_style(g('success'))
        self._name_lbl.color                 = g('text_dim')
        self._value_lbl.color                = g('text_dim')
        self._editor_card.bgcolor            = g('card_bg')
        self._editor_card.border             = _border_all(1, g('card_border'))

        if self._name_inp.error:
            err_color = g('danger')
            self._name_inp.border_color         = err_color
            self._name_inp.focused_border_color = err_color

        if self._current_view == 'list':
            self._refresh_list()

        self._page.update()

    def _build_controls(self):
        self._build_list_view()
        self._build_editor_view()

    def _build_list_view(self):
        self._header_title = ft.Text(
            _t('variables') or 'Variables',
            size=15,
            weight=ft.FontWeight.BOLD,
            color=_c('text'),
        )
        self._search_inp = ft.TextField(
            hint_text=_t('search') or 'Search',
            height=40,
            width=180,
            content_padding=ft.Padding(left=10, right=10, top=0, bottom=0),
            bgcolor=_c('card_bg'),
            border_color=_c('card_border'),
            border_radius=8,
            on_change=lambda _: self._refresh_list(),
        )

        header = ft.Container(
            content=ft.Column(
                [
                    self._count_label,
                    ft.Row(
                        [self._header_title, self._search_inp],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=2,
            ),
            padding=ft.Padding(left=12, right=12, top=6, bottom=6),
            height=66, # تم زيادة الارتفاع قليلاً ليتناسب مع العداد
        )

        self._grid = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

        self._empty_lbl = ft.Container(
            content=ft.Text(
                _t('no_variables') or 'No variables found.',
                size=13,
                color=_c('text_dim'),
                text_align=ft.TextAlign.CENTER,
            ),
            alignment=ft.Alignment(0, 0),
            height=120,
            visible=False,
        )

        self._fab = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            bgcolor=_c('accent'),
            foreground_color=_c('text_on_accent'),
            mini=True,
            on_click=lambda _: self._open_editor(''),
        )

        self._list_root = ft.Column(
            [
                header,
                ft.Container(
                    content=ft.Stack(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [self._empty_lbl, self._grid],
                                    spacing=0,
                                    scroll=ft.ScrollMode.AUTO,
                                    expand=True,
                                ),
                                padding=ft.Padding(left=12, right=12, top=8, bottom=0),
                                expand=True,
                            ),
                            ft.Container(
                                content=self._fab,
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

    def _build_editor_view(self):
        self._back_btn = ft.IconButton(
            icon=ft.Icons.ARROW_BACK_ROUNDED,
            icon_color=_c('text_on_accent'),
            bgcolor=_c('accent'),
            icon_size=16,
            on_click=self._request_back,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )
        self._editor_breadcrumb = ft.Text(
            _t('variables_slash') or "Variable's /", size=13, color=_c('text_dim'),
        )
        self._editor_title = ft.Text(
            _ar('new.json'), size=13, weight=ft.FontWeight.BOLD, color=_c('text'),
        )
        self._dirty_dot = ft.Container(
            width=7, height=7,
            bgcolor=_c('warning'),
            border_radius=4,
            visible=False,
            tooltip=_t('unsaved_title'),
        )
        self._scoped_btn = ft.IconButton(
            icon=ft.Icons.MENU_ROUNDED,
            icon_color=_c('text_dim'),
            icon_size=18,
            tooltip=_t('scoped_vars') or 'Per-user values',
            visible=False,
            on_click=lambda _: self._open_json_editor(self._name_inp.value or ''),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )

        self._name_lbl  = ft.Text(_t('name_label')  or 'Name',  size=10, weight=ft.FontWeight.BOLD, color=_c('text_dim'))
        self._value_lbl = ft.Text(_t('value_label') or 'Value', size=10, weight=ft.FontWeight.BOLD, color=_c('text_dim'))

        self._name_inp = ft.TextField(
            hint_text=_t('var_name_hint') or 'variable_name',
            dense=True,
            bgcolor=_c('card_bg'),
            border_color=_c('card_border'),
            focused_border_color=_c('accent'),
            cursor_color=_c('accent'),
            text_style=ft.TextStyle(color=_c('text'), size=13),
            border_radius=8,
            expand=True,
            on_change=self._mark_dirty,
        )
        self._value_inp = ft.TextField(
            hint_text=_t('var_value_hint') or 'variable_value',
            dense=True,
            bgcolor=_c('card_bg'),
            border_color=_c('card_border'),
            focused_border_color=_c('accent'),
            cursor_color=_c('accent'),
            text_style=ft.TextStyle(color=_c('text'), size=13),
            border_radius=8,
            expand=True,
            on_change=self._mark_dirty,
        )

        self._save_btn = ft.FilledButton(
            content=ft.Row(
                [ft.Icon(ft.Icons.SAVE_OUTLINED, color='#FFFFFF', size=16),
                 ft.Text(_t('save') or 'Save', color='#FFFFFF', weight=ft.FontWeight.BOLD)],
                spacing=6, tight=True,
            ),
            on_click=self._save_variable,
            style=_btn_style(_c('success')),
        )

        self._editor_card = ft.Container(
            content=ft.Column(
                [
                    ft.Column([self._name_lbl,  self._name_inp],  spacing=4),
                    ft.Divider(height=1, color=_c('card_border')),
                    ft.Column([self._value_lbl, self._value_inp], spacing=4),
                ],
                spacing=12,
            ),
            bgcolor=_c('card_bg'),
            border=_border_all(1, _c('card_border')),
            border_radius=12,
            padding=ft.Padding(left=14, right=14, top=12, bottom=12),
        )

        self._editor_root = ft.Column(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            self._back_btn,
                            self._editor_breadcrumb,
                            self._editor_title,
                            self._dirty_dot,
                            ft.Container(expand=True),
                            self._scoped_btn,
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(left=10, right=10, top=6, bottom=6),
                    height=46,
                ),
                ft.Stack(
                    [
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(_t('info_var') or 'Info Variable', size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=_c('text_dim')),
                                    self._editor_card,
                                    ft.Container(height=70),
                                ],
                                spacing=10,
                                expand=True,
                                scroll=ft.ScrollMode.ADAPTIVE,
                            ),
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

    def _show_list(self):
        _sync_fdcore(self._bot_dir)
        self._current_view      = 'list'
        self._container.content = self._list_root
        self._update_vars_count()
        self._refresh_list()
        self._page.update()

    def _open_editor(self, var_path: str):
        self._edit_path    = var_path
        self._current_view = 'editor'

        if not var_path:
            self._name_inp.value     = ''
            self._value_inp.value    = ''
            self._editor_title.value = _ar('new.json')
        else:
            var  = next((v for v in self._variables if v.get('_path') == var_path), {})
            name = var.get('name', '')
            self._name_inp.value     = name
            self._value_inp.value    = var.get('value', '')
            self._editor_title.value = _ar(f'{name}.json')

        self._update_scoped_btn_visibility()
        self._clear_name_error()
        self._clear_dirty()

        self._container.content = self._editor_root
        self._page.update()

    def _update_scoped_btn_visibility(self):
        name = (self._name_inp.value or '').strip()
        self._scoped_btn.visible = bool(name)

    def _refresh_list(self):
        if self._bot_dir:
            self._variables = _load_all_vars(self._bot_dir)
            self._ids_data  = _load_ids_data(self._bot_dir)

        seen   = set()
        unique = []
        for v in self._variables:
            key = v.get('_path', id(v))
            if key not in seen:
                seen.add(key)
                unique.append(v)
        self._variables = unique
    
        self._grid.controls.clear()
    
        q = (self._search_inp.value or '').strip().lower()
        filtered = [
            v for v in self._variables
            if not q
            or q in v.get('name',  '').lower()
            or q in v.get('value', '').lower()
        ]
    
        self._empty_lbl.visible = (len(filtered) == 0)
    
        for num, var in enumerate(filtered, start=1):
            self._grid.controls.append(self._var_card(num, var))
            
        if filtered:
            self._grid.controls.append(ft.Container(height=60))
        
        self._update_vars_count()
        self._page.update()

    def _var_card(self, num: int, var: dict) -> ft.Control:
        path = var.get('_path', '')
        name = var.get('name', '')
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
                                    ft.Text(_ar(name), size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color=_c('text')),
                                    ft.Text(_ar(var.get('value', '') or '—'), size=11,
                                            color=_c('text_dim')),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.FilledButton(
                                content=ft.Text(_t('edit') or 'Edit',
                                                color=_c('text_on_accent')),
                                on_click=lambda _, p=path: self._open_editor(p),
                                style=_btn_style(
                                    _c('accent'),
                                    _c('text_on_accent'),
                                    ft.Padding(left=10, right=10, top=4, bottom=4),
                                ),
                            ),
                            ft.FilledButton(
                                content=ft.Text(_t('del') or 'Del', color='#FFFFFF'),
                                on_click=lambda _, p=path, n=name: self._ask_delete(p, n),
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
                    border=_border_all(1, _c('card_border')),
                    border_radius=10,
                    padding=ft.Padding(left=10, right=10, top=8, bottom=8),
                    expand=True,
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _ask_delete(self, path: str, name: str):
        _confirm_delete(
            self._page,
            item_name=name,
            on_confirm=lambda: self._do_delete(path),
        )

    def _do_delete(self, path: str):
        _delete_var(path)
        _sync_fdcore(self._bot_dir)
        self._show_list()

    def _perform_save(self) -> bool:
        name  = (self._name_inp.value  or '').strip()
        value = (self._value_inp.value or '').strip()

        if not name:
            self._set_name_error()
            if self._page:
                self._page.update()
            return False

        safe_name = ''.join(c for c in name if c.isalnum() or c in ('-', '_')).strip() or 'var'

        if _var_file_exists(self._bot_dir, safe_name, self._edit_path):
            self._set_name_taken_error()
            if self._page:
                self._page.update()
            return False

        self._clear_name_error()

        if not self._bot_dir:
            print('[Variables] bot_dir not set')
            return False

        _sync_fdcore(self._bot_dir)
        self._edit_path = _write_var(
            self._bot_dir, name, value, self._edit_path
        )

        self._editor_title.value = _ar(f'{name}.json')
        self._variables = _load_all_vars(self._bot_dir)
        self._update_vars_count()
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

        return True

    def _save_variable(self, _):
        if self._perform_save():
            self._show_list()

    def _build_json_editor_dialog(self):
        self._json_editor_title = ft.Text(
            '', size=14, weight=ft.FontWeight.BOLD, color=_c('text'),
        )
        self._json_editor_error_lbl = ft.Text(
            '', size=12, color=_c('danger'), visible=False,
        )
        self._json_editor = ft.TextField(
            value='{}',
            multiline=True,
            min_lines=18,
            max_lines=None,
            expand=True,
            border=ft.InputBorder.NONE,
            bgcolor='transparent',
            color=_c('text'),
            cursor_color=_c('accent'),
            text_style=ft.TextStyle(
                font_family='Consolas, Menlo, monospace', size=13,
            ),
            content_padding=ft.Padding(left=4, right=4, top=4, bottom=4),
            on_change=lambda _: self._mark_json_dirty(),
        )
        self._json_editor_dirty_dot = ft.Container(
            width=7, height=7,
            bgcolor=_c('warning'),
            border_radius=4,
            visible=False,
            tooltip=_t('unsaved_title'),
        )

        editor_box = ft.Container(
            content=self._json_editor,
            bgcolor=_c('card_bg'),
            border=_border_all(1, _c('card_border')),
            border_radius=10,
            padding=6,
            width=560,
            height=420,
        )

        self._json_editor_dialog = ft.AlertDialog(
            modal=True,
            bgcolor=_c('card_bg'),
            shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.DATA_OBJECT_ROUNDED, color=_c('accent'), size=20),
                    self._json_editor_title,
                    self._json_editor_dirty_dot,
                ],
                spacing=8,
            ),
            content=ft.Column(
                [editor_box, self._json_editor_error_lbl],
                spacing=8,
                tight=True,
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text(_t('cancel') or 'Cancel', color=_c('text_dim')),
                    on_click=self._request_close_json_editor,
                ),
                ft.FilledButton(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.SAVE_OUTLINED, color='#FFFFFF', size=16),
                         ft.Text(_t('save') or 'Save', color='#FFFFFF',
                                 weight=ft.FontWeight.BOLD)],
                        spacing=6, tight=True,
                    ),
                    on_click=self._save_json_editor,
                    style=_btn_style(_c('success')),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _mark_json_dirty(self):
        if not self._json_editor_dirty:
            self._json_editor_dirty = True
            self._json_editor_dirty_dot.visible = True
            if self._page:
                self._page.update()
        if self._json_editor_error_lbl.visible:
            self._json_editor_error_lbl.visible = False
            if self._page:
                self._page.update()

    def _open_json_editor(self, name: str):
        self._json_editor_var   = name
        self._json_editor_dirty = False
        self._json_editor_dirty_dot.visible = False
        self._json_editor_error_lbl.visible = False

        scoped = self._ids_data.get(name, {})
        self._json_editor.value = json.dumps(scoped, ensure_ascii=False, indent=2)
        self._json_editor_title.value = _ar(f'{name} — {_t("scoped_vars") or "Per-user values"}')

        self._page.show_dialog(self._json_editor_dialog)
        self._page.update()

    def _request_close_json_editor(self, _):
        if self._json_editor_dirty:
            _confirm_unsaved(
                self._page,
                on_save=lambda: self._save_json_editor(None),
                on_discard=self._close_json_editor,
            )
        else:
            self._close_json_editor()

    def _close_json_editor(self):
        self._page.pop_dialog()
        self._page.update()

    def _save_json_editor(self, _):
        raw = self._json_editor.value or '{}'
        try:
            parsed = json.loads(raw)
        except Exception as e:
            self._json_editor_error_lbl.value   = f'{_t("invalid_json") or "Invalid JSON"}: {e}'
            self._json_editor_error_lbl.visible = True
            self._page.update()
            return

        if not isinstance(parsed, dict):
            self._json_editor_error_lbl.value   = (
                _t('json_must_be_object') or 'Top level value must be a JSON object.'
            )
            self._json_editor_error_lbl.visible = True
            self._page.update()
            return

        normalized = {str(uid): ('' if v is None else str(v)) for uid, v in parsed.items()}

        if not self._bot_dir:
            print('[Variables] bot_dir not set')
            return

        self._ids_data = _load_ids_data(self._bot_dir)
        if normalized:
            self._ids_data[self._json_editor_var] = normalized
        else:
            self._ids_data.pop(self._json_editor_var, None)
        _save_ids_data(self._bot_dir, self._ids_data)

        self._json_editor_dirty = False
        self._json_editor_dirty_dot.visible = False
        self._close_json_editor()
        self._refresh_list()

        if self._page:
            self._page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(_t('saved_successfully'), color='#FFFFFF'),
                    bgcolor=_c('success'),
                    duration=2000,
                )
            )
            self._page.update()