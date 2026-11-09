# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/variables_view.py . migrated to Flet 0.85.2+ / v1 API

import os
import json
import uuid
import asyncio
import flet as ft

from main_app.langs._translations import Translations
from main_app.settings_app           import get_current_lang
from main_app.theme.theme_engine import ThemeEngine
from main_app.core_fdsb.FDCore   import set_vars_dir as _fd_set_vars_dir

def _vars_dir(bot_dir: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(bot_dir)), 'bot_vars')

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


def _sync_fdcore(bot_dir: str):
    path = _vars_dir(bot_dir)
    os.makedirs(path, exist_ok=True)
    _fd_set_vars_dir(path)

def _bot_root_from_dir(bot_dir: str) -> str:
    return os.path.dirname(os.path.abspath(bot_dir))

def _ids_data_path(bot_dir: str) -> str:
    vars_dir = _vars_dir(bot_dir)
    return os.path.join(os.path.dirname(vars_dir), 'bot_ids', 'ids_data.json')

def _user_vars_dir(bot_dir: str) -> str:
    vars_dir = _vars_dir(bot_dir)
    return os.path.join(os.path.dirname(vars_dir), 'user_vars')

def _guild_vars_dir(bot_dir: str) -> str:
    vars_dir = _vars_dir(bot_dir)
    return os.path.join(os.path.dirname(vars_dir), 'guild_vars')

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

def _safe_name(name: str) -> str:
    return ''.join(c for c in name if c.isalnum() or c in ('-', '_')).strip() or 'var'

def _load_scoped_var(base_dir: str, name: str) -> dict:
    if not base_dir:
        return {}
    path = os.path.join(base_dir, f'{_safe_name(name)}.json')
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        values = data.get('values') if isinstance(data, dict) else None
        return values if isinstance(values, dict) else {}
    except Exception:
        return {}

def _save_scoped_var(base_dir: str, name: str, values: dict):
    if not base_dir:
        return
    os.makedirs(base_dir, exist_ok=True)
    path = os.path.join(base_dir, f'{_safe_name(name)}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'name': name, 'values': values}, f, ensure_ascii=False, indent=2)

def _delete_scoped_file(base_dir: str, name: str):
    path = os.path.join(base_dir, f'{_safe_name(name)}.json')
    if os.path.isfile(path):
        try:
            os.remove(path)
        except Exception:
            pass

def _t(key: str) -> str:
    return Translations.get(key, get_current_lang())

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

    msg_template  = _t('delete_confirm')
    formatted_msg = msg_template.replace('{item_name}', item_name)

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
        content=ft.Text(_ar(formatted_msg), color=_c('text_dim'), size=13),
        actions=[
            ft.TextButton(
                content=ft.Text(_t('cancel'), color=_c('text_dim')),
                on_click=_cancel,
            ),
            ft.FilledButton(
                content=ft.Row(
                    [ft.Icon(ft.Icons.DELETE_FOREVER_ROUNDED, color='#FFFFFF', size=16),
                     ft.Text(_t('delete'), color='#FFFFFF',
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

def _ensure_vars_dir(bot_dir: str) -> str:
    path = _vars_dir(bot_dir)
    os.makedirs(path, exist_ok=True)
    return path

def _var_file_exists(bot_dir: str, safe_name: str, exclude_path: str = '') -> bool:
    exclude_abs = os.path.abspath(exclude_path) if exclude_path else ''
    candidate = os.path.join(_vars_dir(bot_dir), f'{safe_name}.json')
    if os.path.isfile(candidate) and os.path.abspath(candidate) != exclude_abs:
        return True
    return False

# ── Creation order: every item stores its own number (max + 1 when created) ──
def _birth_ns(st):
    """Real creation time in ns, or None when the platform does not provide it
    (Windows and macOS do, Linux/Android do not)."""
    b = getattr(st, 'st_birthtime_ns', None)
    if b:
        return b
    b = getattr(st, 'st_birthtime', None)
    if b:
        return int(b * 1e9)
    if os.name == 'nt':
        return st.st_ctime_ns
    return None

def _assign_missing_orders(paths: list, existing_max: int = 0) -> dict:
    """Numbers for files created before the order existed: oldest first by real
    creation time when available, otherwise alphabetical, after existing_max."""
    births = {}
    for p in paths:
        try:
            births[p] = _birth_ns(os.stat(p))
        except OSError:
            births[p] = None
    name_key = lambda p: os.path.basename(p).lower()
    if paths and all(births[p] is not None for p in paths):
        ordered = sorted(paths, key=lambda p: (births[p], name_key(p)))
    else:
        ordered = sorted(paths, key=name_key)
    return {p: existing_max + i + 1 for i, p in enumerate(ordered)}

def _read_var_order(path: str):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        n = data.get('order') if isinstance(data, dict) else None
        return n if isinstance(n, int) and not isinstance(n, bool) else None
    except Exception:
        return None

def _has_order(v: dict) -> bool:
    n = v.get('order')
    return isinstance(n, int) and not isinstance(n, bool)

def _var_ensure_orders(bot_dir: str, items: list) -> list:
    """One-time numbering of variables created before the order system existed."""
    existing_max = max((v['order'] for v in items if _has_order(v)), default=0)
    legacy = [v for v in items if not _has_order(v) and v.get('_path')]
    if legacy:
        nums = _assign_missing_orders([v['_path'] for v in legacy], existing_max)
        for v in legacy:
            v['order'] = nums[v['_path']]
            try:
                with open(v['_path'], 'w', encoding='utf-8') as f:
                    json.dump({k: val for k, val in v.items() if k != '_path'},
                              f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f'[Variables] order write failed: {e}')
    return items

def _var_next_order(bot_dir: str) -> int:
    items = []
    d = _vars_dir(bot_dir)
    if os.path.isdir(d):
        for fname in os.listdir(d):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(d, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data['_path'] = fpath
                    items.append(data)
            except Exception:
                pass
    _var_ensure_orders(bot_dir, items)
    return max((v['order'] for v in items if _has_order(v)), default=0) + 1

def _load_all_vars(bot_dir: str) -> list:
    d = _vars_dir(bot_dir)
    os.makedirs(d, exist_ok=True)
    result = []
    loaded_names = set()

    if os.path.isdir(d):
        for fname in sorted(os.listdir(d)):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(d, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data['_path'] = fpath
                    name = data.get('name', '')
                    if name:
                        loaded_names.add(name)
                    result.append(data)
            except Exception as e:
                print(f'[Variables] load error {fpath}: {e}')

    _var_ensure_orders(bot_dir, result)

    uv_dir = _user_vars_dir(bot_dir)
    if os.path.isdir(uv_dir):
        for fname in sorted(os.listdir(uv_dir)):
            if fname.endswith('.json'):
                try:
                    with open(os.path.join(uv_dir, fname), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    name = data.get('name', '')
                    if name and name not in loaded_names:
                        p = _write_var(bot_dir, name, '')
                        loaded_names.add(name)
                        result.append({'name': name, 'value': '', '_path': p,
                                       'order': _read_var_order(p)})
                except Exception:
                    pass

    gv_dir = _guild_vars_dir(bot_dir)
    if os.path.isdir(gv_dir):
        for fname in sorted(os.listdir(gv_dir)):
            if fname.endswith('.json'):
                try:
                    with open(os.path.join(gv_dir, fname), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    name = data.get('name', '')
                    if name and name not in loaded_names:
                        p = _write_var(bot_dir, name, '')
                        loaded_names.add(name)
                        result.append({'name': name, 'value': '', '_path': p,
                                       'order': _read_var_order(p)})
                except Exception:
                    pass

    # oldest first, newest last (by the creation number stored in the file)
    result.sort(key=lambda v: v['order'] if _has_order(v) else 0)
    return result

def _write_var(bot_dir: str, name: str, value: str, old_path: str = '',
               folder: str = '') -> str:
    safe = _safe_name(name)
    new_path = os.path.join(_vars_dir(bot_dir), f'{safe}.json')

    # keep the creation number of an existing file (also on rename),
    # otherwise take the next one from the shared counter
    order = None
    for p in (old_path, new_path):
        if p and os.path.isfile(p):
            order = _read_var_order(p)
            if order is not None:
                break
    if order is None:
        order = _var_next_order(bot_dir)

    if old_path and os.path.abspath(old_path) != os.path.abspath(new_path):
        if os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
    _ensure_vars_dir(bot_dir)
    with open(new_path, 'w', encoding='utf-8') as f:
        data = {'name': name, 'value': value, 'order': order}
        if folder:
            data['folder'] = folder
        json.dump(data, f, ensure_ascii=False, indent=2)
    return new_path

def _delete_var(bot_dir: str, path: str, name: str):
    if os.path.isfile(path):
        try:
            os.remove(path)
        except Exception:
            pass
    _delete_scoped_file(_user_vars_dir(bot_dir), name)
    _delete_scoped_file(_guild_vars_dir(bot_dir), name)
    ids_data = _load_ids_data(bot_dir)
    if name in ids_data:
        ids_data.pop(name, None)
        _save_ids_data(bot_dir, ids_data)


# ═════════════════════════════════════════════════════════════════════════
#  Folders
#  • Each variable file (bot_vars/<name>.json) gets an optional "folder": "<id>"
#    key. The files never move, so FDCore keeps reading them as before.
#  • The folder tree (id → name / parent / creation number) lives in ONE small
#    file OUTSIDE bot_vars (bot_folders/variables.json), because every .json
#    inside bot_vars is treated as a variable.
#  • Folders nest to any depth. Inside a folder, variables are shown in
#    creation order (the "order" number).
# ═════════════════════════════════════════════════════════════════════════
_INDENT_PX = 16
_MAX_INDENT_LEVELS = 6


def _folders_file(bot_dir: str) -> str:
    root = os.path.dirname(_vars_dir(bot_dir))
    return os.path.join(root, 'bot_folders', 'variables.json')

def _load_folders(bot_dir: str) -> dict:
    """{id: {'name', 'parent', 'order'}}  (parent '' = top level). Self-repairing:
    a missing parent or a loop turns the folder into a top-level one."""
    try:
        with open(_folders_file(bot_dir), 'r', encoding='utf-8') as f:
            data = json.load(f)
        raw = data.get('folders', {}) if isinstance(data, dict) else {}
    except Exception:
        return {}

    folders = {}
    for fid, f in (raw or {}).items():
        if not isinstance(f, dict):
            continue
        name = str(f.get('name') or '').strip()
        if not name:
            continue
        try:
            order = int(f.get('order') or 0)
        except (TypeError, ValueError):
            order = 0
        folders[str(fid)] = {'name': name, 'parent': str(f.get('parent') or ''),
                             'order': order}

    for f in folders.values():
        if f['parent'] not in folders:
            f['parent'] = ''
    for fid in folders:
        seen, cur = set(), fid
        while cur:
            if cur in seen:
                folders[fid]['parent'] = ''
                break
            seen.add(cur)
            cur = folders[cur]['parent']
    return folders

def _save_folders(bot_dir: str, folders: dict) -> bool:
    try:
        path = _folders_file(bot_dir)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({'folders': folders}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception as e:
        print(f'[Variables] folders save failed: {e}')
        return False

def _folder_children(folders: dict) -> dict:
    """{parent_id: [child ids]} oldest folder first."""
    kids = {}
    for fid, f in folders.items():
        kids.setdefault(f['parent'], []).append(fid)
    for lst in kids.values():
        lst.sort(key=lambda i: (folders[i]['order'], folders[i]['name'].lower()))
    return kids

def _folder_descendants(folders: dict, fid: str) -> set:
    """fid itself plus every folder below it, at any depth."""
    out = {fid}
    changed = True
    while changed:
        changed = False
        for i, f in folders.items():
            if i not in out and f['parent'] in out:
                out.add(i)
                changed = True
    return out

def _folder_path(folders: dict, fid: str, sep: str = ' / ') -> str:
    parts, seen = [], set()
    while fid and fid in folders and fid not in seen:
        seen.add(fid)
        parts.append(folders[fid]['name'])
        fid = folders[fid]['parent']
    return sep.join(reversed(parts))

def _folder_name_taken(folders: dict, parent: str, name: str, exclude: str = '') -> bool:
    low = name.strip().lower()
    return any(
        fid != exclude and f['parent'] == parent and f['name'].lower() == low
        for fid, f in folders.items()
    )

def _make_name_validator(bot_dir: str, parent: str, exclude: str = ''):
    """Returns validate(name) -> error text or None (reads the tree fresh)."""
    def _v(name: str):
        if not name:
            return _t('folder_name_required')
        if _folder_name_taken(_load_folders(bot_dir), parent, name, exclude):
            return _t('folder_name_taken')
        return None
    return _v

def _create_folder(bot_dir: str, name: str, parent: str = '') -> str:
    """Create a folder (any name is fine) and return its id, '' on failure."""
    folders = _load_folders(bot_dir)
    if parent not in folders:
        parent = ''
    fid   = uuid.uuid4().hex[:8]
    order = max((f['order'] for f in folders.values()), default=0) + 1
    folders[fid] = {'name': name.strip(), 'parent': parent, 'order': order}
    return fid if _save_folders(bot_dir, folders) else ''

def _rename_folder(bot_dir: str, fid: str, name: str) -> bool:
    folders = _load_folders(bot_dir)
    if fid not in folders:
        return False
    folders[fid]['name'] = name.strip()
    return _save_folders(bot_dir, folders)

def _move_folder(bot_dir: str, fid: str, new_parent: str) -> bool:
    folders = _load_folders(bot_dir)
    if fid not in folders or new_parent in _folder_descendants(folders, fid):
        return False                       # can't move a folder into itself / its children
    if new_parent not in folders:
        new_parent = ''
    folders[fid]['parent'] = new_parent
    return _save_folders(bot_dir, folders)

def _var_files(bot_dir: str) -> list:
    """Raw variable files of bot_vars (each dict carries its '_path')."""
    out, d = [], _vars_dir(bot_dir)
    if not os.path.isdir(d):
        return out
    for fname in os.listdir(d):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(d, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                data['_path'] = fpath
                out.append(data)
        except Exception:
            pass
    return out

def _set_var_folder(path: str, folder_id: str) -> bool:
    """Rewrite only the "folder" key of an existing variable file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return False
        if folder_id:
            data['folder'] = folder_id
        else:
            data.pop('folder', None)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f'[Variables] folder write failed: {e}')
        return False

def _delete_folder(bot_dir: str, fid: str) -> bool:
    """Delete only the folder: its variables and sub-folders move up one level."""
    folders = _load_folders(bot_dir)
    if fid not in folders:
        return False
    parent = folders[fid]['parent']
    for v in _var_files(bot_dir):
        if v.get('folder') == fid:
            _set_var_folder(v['_path'], parent)
    for f in folders.values():
        if f['parent'] == fid:
            f['parent'] = parent
    del folders[fid]
    return _save_folders(bot_dir, folders)

def _build_level_rows(variables: list, folders: dict, cur: str) -> list:
    """Rows of ONE folder level: its sub-folders first (oldest first), then its
    variables in creation order, numbered 1..n."""
    kids  = _folder_children(folders)
    files = {}
    for v in variables:                     # already sorted by "order"
        fid = v.get('folder') or ''
        if fid not in folders:
            fid = ''
        files.setdefault(fid, []).append(v)

    totals = {}
    def total(fid):
        if fid not in totals:
            totals[fid] = len(files.get(fid, [])) + sum(total(k) for k in kids.get(fid, []))
        return totals[fid]

    rows = [{'kind': 'folder', 'id': fid, 'name': folders[fid]['name'],
             'count': total(fid)} for fid in kids.get(cur, [])]
    for n, v in enumerate(files.get(cur, []), 1):
        r = dict(v)
        r.update(kind='var', num=n)
        rows.append(r)
    return rows


def _dlg_text_field(label: str, value: str = '', **kw) -> ft.TextField:
    return ft.TextField(
        value=value, label=label, dense=True,
        border_color=_c('card_border'), focused_border_color=_c('accent'),
        label_style=ft.TextStyle(color=_c('text_dim'), size=11),
        text_style=ft.TextStyle(color=_c('text'), size=13),
        cursor_color=_c('accent'), bgcolor=_c('card_bg'),
        **kw,
    )

def _dlg_title(icon, text: str, color: str = None) -> ft.Row:
    return ft.Row(
        [ft.Icon(icon, color=color or _c('accent'), size=22),
         ft.Text(text, weight=ft.FontWeight.BOLD, color=_c('text'), size=16,
                 max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True)],
        spacing=8,
    )

def _prompt_folder_name(page: ft.Page, title: str, initial: str,
                        validate: callable, on_ok: callable):
    """Small dialog asking for a folder name. validate(name) -> error text / None."""
    field = _dlg_text_field(_t('folder_new_name'), initial, autofocus=True)

    def _clear(_=None):
        if field.error:
            field.error = None
            page.update()

    def _ok(_=None):
        name = (field.value or '').strip()
        err = validate(name)
        if err:
            field.error = err
            page.update()
            return
        page.pop_dialog()
        on_ok(name)

    field.on_change = _clear
    field.on_submit = _ok

    page.show_dialog(ft.AlertDialog(
        modal=True,
        bgcolor=_c('card_bg'),
        shape=ft.RoundedRectangleBorder(radius=16),
        title=_dlg_title(ft.Icons.CREATE_NEW_FOLDER_OUTLINED, title),
        content=ft.Container(content=field, width=300),
        actions=[
            ft.TextButton(content=ft.Text(_t('cancel'), color=_c('text_dim')),
                          on_click=lambda _: page.pop_dialog()),
            ft.FilledButton(
                content=ft.Text(_t('ok'), color=_c('text_on_accent'),
                                weight=ft.FontWeight.BOLD),
                on_click=_ok,
                style=ft.ButtonStyle(
                    bgcolor=_c('accent'), color=_c('text_on_accent'),
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding(left=14, top=8, right=14, bottom=8)),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    ))

def _folder_picker(page: ft.Page, bot_dir: str, selected: str,
                   on_pick: callable, exclude_root: str = ''):
    """Tree dialog: pick where something lives, or create a new folder (inside
    whatever is highlighted) and pick it. '' = top level (no folder).
    exclude_root: when moving a folder, it and everything below it is hidden."""
    st = {'sel': selected or '', 'folders': _load_folders(bot_dir)}
    blocked = _folder_descendants(st['folders'], exclude_root) if exclude_root else set()

    tree_col  = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
    where_lbl = ft.Text('', size=10, italic=True, color=_c('text_dim'))
    new_field = _dlg_text_field(_t('folder_new_name'), expand=True)

    def _row(fid: str, name: str, depth: int, icon) -> ft.Control:
        sel = fid == st['sel']
        fg  = _c('text_on_accent') if sel else _c('text')
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=min(depth, _MAX_INDENT_LEVELS) * _INDENT_PX,
                                 visible=depth > 0),
                    ft.Icon(icon, size=18, color=fg),
                    ft.Text(name, size=12, color=fg, expand=True,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Icon(ft.Icons.CHECK_ROUNDED, size=16, color=fg, visible=sel),
                ],
                spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=_c('accent') if sel else None,
            border_radius=8,
            padding=ft.Padding(left=8, right=8, top=8, bottom=8),
            on_click=lambda _, i=fid: _select(i),
        )

    def _fill():
        folders  = st['folders']
        children = _folder_children(folders)
        rows = [_row('', _t('folder_root'), 0, ft.Icons.HOME_ROUNDED)]

        def walk(parent, depth):
            for fid in children.get(parent, []):
                if fid in blocked:
                    continue
                rows.append(_row(fid, folders[fid]['name'], depth,
                                 ft.Icons.FOLDER_ROUNDED))
                walk(fid, depth + 1)

        walk('', 1)
        tree_col.controls = rows
        where = _folder_path(folders, st['sel']) or _t('folder_root')
        where_lbl.value = f"{_t('folder_create_in')}: {where}"

    def _select(fid: str):
        st['sel'] = fid
        _fill()
        page.update()

    def _add(_=None):
        name = (new_field.value or '').strip()
        err = _make_name_validator(bot_dir, st['sel'])(name)
        if err:
            new_field.error = err
            page.update()
            return
        fid = _create_folder(bot_dir, name, st['sel'])
        if not fid:
            return
        st['folders'] = _load_folders(bot_dir)
        st['sel'] = fid                    # the new folder becomes the chosen one
        new_field.value = ''
        new_field.error = None
        _fill()
        page.update()

    def _clear_err(_=None):
        if new_field.error:
            new_field.error = None
            page.update()

    def _done(_=None):
        page.pop_dialog()
        on_pick(st['sel'])

    new_field.on_submit = _add
    new_field.on_change = _clear_err
    _fill()

    page.show_dialog(ft.AlertDialog(
        modal=True,
        bgcolor=_c('card_bg'),
        shape=ft.RoundedRectangleBorder(radius=16),
        title=_dlg_title(ft.Icons.FOLDER_OPEN_ROUNDED, _t('folder_pick_title')),
        content=ft.Container(
            width=330,
            content=ft.Column(
                [
                    ft.Container(
                        content=tree_col, height=240,
                        border=_border_all(1, _c('card_border')),
                        border_radius=8, padding=4,
                    ),
                    ft.Row(
                        [
                            new_field,
                            ft.IconButton(
                                icon=ft.Icons.CREATE_NEW_FOLDER_OUTLINED,
                                icon_color=_c('accent'), icon_size=22,
                                tooltip=_t('folder_new'), on_click=_add,
                            ),
                        ],
                        spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    where_lbl,
                ],
                tight=True, spacing=8,
            ),
        ),
        actions=[
            ft.TextButton(content=ft.Text(_t('cancel'), color=_c('text_dim')),
                          on_click=lambda _: page.pop_dialog()),
            ft.FilledButton(
                content=ft.Text(_t('folder_select'), color=_c('text_on_accent'),
                                weight=ft.FontWeight.BOLD),
                on_click=_done,
                style=ft.ButtonStyle(
                    bgcolor=_c('accent'), color=_c('text_on_accent'),
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding(left=14, top=8, right=14, bottom=8)),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    ))

def _confirm_folder_delete(page: ft.Page, name: str, on_confirm: callable):
    def _do(_):
        page.pop_dialog()
        on_confirm()

    page.show_dialog(ft.AlertDialog(
        modal=True,
        bgcolor=_c('card_bg'),
        shape=ft.RoundedRectangleBorder(radius=16),
        title=_dlg_title(ft.Icons.WARNING_AMBER_ROUNDED,
                         f"{_t('folder_delete')}: {name}", _c('danger')),
        content=ft.Text(_t('folder_delete_body'), color=_c('text_dim'), size=13),
        actions=[
            ft.TextButton(content=ft.Text(_t('cancel'), color=_c('text_dim')),
                          on_click=lambda _: page.pop_dialog()),
            ft.FilledButton(
                content=ft.Text(_t('delete'), color='#FFFFFF', weight=ft.FontWeight.BOLD),
                on_click=_do,
                style=ft.ButtonStyle(
                    bgcolor=_c('danger'), color='#FFFFFF',
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding(left=14, top=8, right=14, bottom=8)),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    ))


# ── Windowed (virtual) list ───────────────────────────────────────────────
# Same mechanism as the wiki list: only ~12-24 rows exist at any time; everything
# above / below the window is stood in for by the list padding, so the scrollbar
# and scroll position behave as if all rows were there. Rows have a FIXED height.
class _VirtualList:
    WIN_STEP    = 12   # rows added / removed per step
    WIN_MAX     = 24   # max rows alive at once
    AHEAD_MIN   = 5    # rows that must exist in the direction of travel
    BEHIND_MIN  = 2    # ... and behind it
    BEHIND_KEEP = 4    # rows kept behind the viewport when the window moves

    def __init__(self, page: ft.Page, build_item: callable,
                 item_height: float, gap: float = 10, bottom_pad: float = 60):
        """build_item(number, item) -> control of exactly `item_height` px."""
        self._page       = page
        self._build_item = build_item
        self._h          = item_height
        self._gap        = gap
        self._ext        = item_height + gap
        self._bottom     = bottom_pad

        self._items: list = []
        self._cache: dict = {}
        self._lo = 0
        self._hi = 0
        self._msg_mode    = True     # showing a message (loading / empty) instead of rows
        self._resetting   = False
        self._disposed    = False
        self._scroll_pix  = 0.0
        self._scroll_view = 600.0
        self._last_pix    = 0.0
        self._going_down  = True
        self._sync_running = False

        self.control = ft.ListView(
            expand=True, spacing=0,
            padding=ft.Padding(0, 0, 0, bottom_pad),
            item_extent=self._ext,
            on_scroll=self._on_scroll, scroll_interval=50,
        )

    # ── public API ───────────────────────────────────────────────────────────
    def dispose(self):
        self._disposed = True
        self._cache.clear()

    def show_message(self, control: ft.Control):
        """Loading / empty state: one free-height control, no windowing."""
        self._items = []
        self._cache.clear()
        self._lo = self._hi = 0
        self._msg_mode = True
        self._clear_rows()
        self.control.item_extent = None
        self.control.padding = ft.Padding(0, 0, 0, self._bottom)
        self.control.controls = [control]
        self._scroll_pix = 0.0
        self._last_pix = 0.0
        self._going_down = True

    def set_items(self, items: list, reset: bool = True):
        """Replace the data. reset=True -> back to the top (search / re-mounted
        list); reset=False -> stay where the user is (theme change, delete, poll)."""
        n = len(items)
        if n == 0:
            self.show_message(ft.Container(height=0))
            return

        keep = (not reset) and (not self._msg_mode)
        had_offset = self._scroll_pix > 0

        # Two-step swap: first remove the old rows on the client, then add the new
        # ones. Patching old rows into new ones in place is what could leave a
        # freshly added row drawn twice until the next refresh.
        self._clear_rows()

        self._items = list(items)
        self._cache.clear()           # rows are rebuilt from the new data
        self._msg_mode = False

        target = min(n - 1, int(self._scroll_pix // self._ext)) if keep else 0
        self._lo = max(0, target - self.WIN_STEP)
        self._hi = min(n, target + self.WIN_STEP)
        self._apply_window()

        if not keep:
            self._last_pix = 0.0
            self._scroll_pix = 0.0
            self._going_down = True
            if had_offset:
                self._scroll_to(0.0)

    # ── internals ────────────────────────────────────────────────────────────
    def _clear_rows(self):
        """Empty the list on the client WITHOUT touching its padding, so the scroll
        extent (and therefore the scroll offset) survives the swap."""
        lv = self.control
        if not lv.controls:
            return
        lv.controls = []
        try:
            lv.update()
        except Exception:
            pass                       # list not mounted yet -> nothing to clear

    def _scroll_to(self, offset: float):
        self._resetting = True

        async def _go():
            try:
                for _ in range(5):
                    try:
                        await self.control.scroll_to(offset=offset, duration=0)
                        break
                    except Exception:
                        # the list may not be mounted yet right after a view switch
                        await asyncio.sleep(0.06)
            finally:
                self._scroll_pix = offset
                self._last_pix = offset
                self._resetting = False
        try:
            self._page.run_task(_go)
        except Exception:
            self._resetting = False

    def _slot(self, idx: int) -> ft.Container:
        return ft.Container(
            content=self._build_item(idx + 1, self._items[idx]),
            height=self._ext,
            padding=ft.Padding(0, 0, 0, self._gap),
        )

    def _apply_window(self):
        """Materialise rows [lo, hi); stand in for all the others with padding."""
        n, lo, hi, ext = len(self._items), self._lo, self._hi, self._ext

        for idx in [i for i in self._cache if i < lo or i >= hi]:
            del self._cache[idx]          # frees the UI objects that left the window

        rows: list = []
        for idx in range(lo, hi):
            row = self._cache.get(idx)
            if row is None:
                row = self._slot(idx)
                self._cache[idx] = row
            rows.append(row)

        # total extent = top + rows + bottom is ALWAYS n * ext (+ bottom margin)
        self.control.item_extent = ext
        self.control.padding = ft.Padding(0, lo * ext, 0, (n - hi) * ext + self._bottom)
        self.control.controls = rows

    def _on_scroll(self, e):
        """Only record the newest position; one worker applies it (events are
        coalesced so the window always follows the LATEST position)."""
        if self._resetting or self._msg_mode or self._disposed:
            return
        self._scroll_pix  = max(0.0, float(e.pixels or 0))
        self._scroll_view = float(getattr(e, 'viewport_dimension', 0) or 600)
        if self._sync_running or len(self._items) <= self.WIN_STEP:
            return
        self._sync_running = True
        try:
            self._page.run_task(self._sync_task)
        except Exception:
            self._sync_running = False

    async def _sync_task(self):
        try:
            while not self._disposed:
                pix = self._scroll_pix
                if self._move_window(pix, self._scroll_view):
                    self.control.update()
                await asyncio.sleep(0.04)
                if self._scroll_pix == pix:          # position settled -> done
                    break
        except Exception as ex:
            print(f'[VirtualList] window sync failed: {ex}')
        finally:
            self._sync_running = False

    def _move_window(self, pix: float, view: float) -> bool:
        n = len(self._items)
        if n <= self.WIN_STEP or self._msg_mode:
            return False

        ext   = self._ext
        first = min(n - 1, int(pix // ext))
        last  = min(n - 1, int((pix + view) // ext))
        vis   = last - first + 1

        delta = pix - self._last_pix
        if abs(delta) >= 2:
            self._going_down = delta > 0
        self._last_pix = pix
        down = self._going_down

        lo, hi = self._lo, self._hi
        cap = max(self.WIN_MAX, vis + self.WIN_STEP)

        below = (hi - 1 - last) if hi < n else 10 ** 6
        above = (first - lo)    if lo > 0 else 10 ** 6
        ahead, behind = (below, above) if down else (above, below)

        covered = first >= lo and last < hi
        if covered and ahead >= self.AHEAD_MIN and behind >= self.BEHIND_MIN:
            return False

        keep = self.BEHIND_KEEP if down else cap - vis - self.BEHIND_KEEP
        new_lo = max(0, min(first - keep, n - cap))
        new_hi = min(n, new_lo + cap)
        if (new_lo, new_hi) == (lo, hi):
            return False

        self._lo, self._hi = new_lo, new_hi
        self._apply_window()
        return True


class BotVariablesTab:
    _ROW_H = 58      # fixed row height -> exact scroll maths for the windowed list
    _GAP   = 10

    def __init__(self, page: ft.Page):
        self._page         = page
        self._bot_dir      = ''
        self._variables    = []
        self._folders: dict = {}
        self._cur_folder   = ''      # folder currently opened in the list
        self._folder_id    = ''      # folder chosen in the editor
        self._ids_data: dict = {}
        self._edit_path    = ''
        self._current_view = 'list'

        self._count_label = ft.Text(
            value="",
            size=11,
            color=_c('text_dim'),
        )

        self._is_dirty  = False
        self._snapshot: dict = {}

        self._poll_task = None
        self._last_sig = None
        self._json_editor_var = ''
        self._json_editor_dirty = False

        self._build_controls()
        self._build_json_editor_dialog()
        self._list_root.key = "vars_list"
        self._editor_root.key = "vars_editor"
        self._container = ft.Container(content=self._list_root, expand=True)

        ThemeEngine.subscribe(self._on_theme)

    def swipe_blocked(self) -> bool:
        return self._current_view == 'editor'

    def handle_back(self) -> bool:
        if getattr(self, '_json_editor_dialog', None) and getattr(self._json_editor_dialog, 'open', False):
            self._request_close_json_editor(None)
            return True
        if self._current_view != 'list':
            self.guard_navigation(self._show_list)
            return True
        if self._cur_folder and not (self._search_inp.value or '').strip():
            self._enter_folder(self._folders.get(self._cur_folder, {}).get('parent', ''))
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
            self._refresh_list(reset=True)

    def _update_vars_count(self):
        count = len(self._variables)
        self._count_label.value = _t('total_vars_count').format(count=count)

    def on_show(self):
        self._last_sig = None
        self._start_polling()

    def on_hide(self):
        self._stop_polling()

    def dispose(self):
        self._stop_polling()
        _theme_unsub(self._on_theme)

    def _dir_signature(self) -> tuple:
        sig = []
        dirs = (_vars_dir(self._bot_dir), _user_vars_dir(self._bot_dir), _guild_vars_dir(self._bot_dir))
        for d in dirs:
            try:
                with os.scandir(d) as it:
                    for e in it:
                        if e.name.endswith('.json'):
                            sig.append((e.name, e.stat().st_mtime_ns))
            except OSError:
                pass
        try:
            st = os.stat(_ids_data_path(self._bot_dir))
            sig.append(('ids_data', st.st_mtime_ns))
        except OSError:
            pass
        try:
            st = os.stat(_folders_file(self._bot_dir))
            sig.append(('folders', st.st_mtime_ns))
        except OSError:
            pass
        return tuple(sorted(sig))

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
                if self._bot_dir and self._current_view == 'list':
                    loop = asyncio.get_event_loop()
                    sig = await loop.run_in_executor(None, self._dir_signature)
                    if sig != self._last_sig:
                        self._last_sig = sig
                        self._refresh_list()
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass

    def _set_name_error(self):
        self._name_inp.error                = _t('enter_variable_name')
        self._name_inp.border_color         = _c('danger')
        self._name_inp.focused_border_color = _c('danger')

    def _set_name_taken_error(self):
        self._name_inp.error                = _t('name_taken')
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
            'name':   self._name_inp.value  or '',
            'value':  self._value_inp.value or '',
            'folder': self._folder_id,
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
            'name':   self._name_inp.value  or '',
            'value':  self._value_inp.value or '',
            'folder': self._folder_id,
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
            self._current_view = 'list'
            self._refresh_list_data(reset=True)
            self._container.content = self._list_root
            self._page.update()
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
        for card in (self._editor_card, self._value_card):
            card.bgcolor                     = g('card_bg')
            card.border                      = _border_all(1, g('card_border'))
        self._folder_lbl.color               = g('text_dim')
        self._folder_box.bgcolor             = g('card_bg')
        self._folder_box.border              = _border_all(1, g('card_border'))
        self._folder_icon.color              = g('accent')
        self._folder_arrow.color             = g('text_dim')
        self._folder_value.color             = g('text') if self._folder_id else g('text_dim')

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
            _t('variables'),
            size=15,
            weight=ft.FontWeight.BOLD,
            color=_c('text'),
        )
        self._search_inp = ft.TextField(
            hint_text=_t('search'),
            height=40,
            width=150,
            content_padding=ft.Padding(left=10, right=10, top=0, bottom=0),
            bgcolor=_c('card_bg'),
            border_color=_c('card_border'),
            border_radius=8,
            on_change=lambda _: self._refresh_list(reset=True),
        )

        header = ft.Container(
            content=ft.Column(
                [
                    self._count_label,
                    ft.Row(
                        [
                            self._header_title,
                            self._search_inp,
                            ft.IconButton(
                                icon=ft.Icons.CREATE_NEW_FOLDER_OUTLINED,
                                icon_color=_c('accent'), icon_size=22,
                                tooltip=_t('folder_new'),
                                on_click=lambda _: self._create_folder_dialog(self._cur_folder),
                            ),
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

        # Breadcrumb bar: where we are (Home > Folder > Sub-folder); each part is tappable
        self._crumbs = ft.Row(spacing=2, scroll=ft.ScrollMode.AUTO,
                              vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self._crumbs_box = ft.Container(
            content=self._crumbs,
            height=34,
            padding=ft.Padding(left=10, right=10, top=0, bottom=0),
        )

        # Windowed list: only ~12-24 rows exist at any time, however many variables there are.
        self._vlist = _VirtualList(self._page, self._var_card, item_height=self._ROW_H,
                                  gap=self._GAP, bottom_pad=60)
        self._grid  = self._vlist.control

        self._empty_lbl = ft.Container(
            content=ft.Text(
                _t('no_variables'),
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
                self._crumbs_box,
                ft.Container(
                    content=ft.Stack(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [self._empty_lbl, self._grid],
                                    spacing=0,
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
            _t('variables_slash'), size=13, color=_c('text_dim'),
        )
        self._editor_title = ft.Text(
            _t('new_variable_file'), size=13, weight=ft.FontWeight.BOLD, color=_c('text'),
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
            tooltip=_t('scoped_vars'),
            visible=False,
            on_click=lambda _: self._open_json_editor(self._name_inp.value or ''),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )

        self._name_lbl  = ft.Text(_t('name_label'),  size=10, weight=ft.FontWeight.BOLD, color=_c('text_dim'))
        self._value_lbl = ft.Text(_t('value_label'), size=10, weight=ft.FontWeight.BOLD, color=_c('text_dim'))

        self._name_inp = ft.TextField(
            hint_text=_t('var_name_hint'),
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
            hint_text=_t('var_value_hint'),
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

        # folder selector: looks like a field, opens the folder tree dialog
        self._folder_lbl   = ft.Text(_t('folder_label'), size=10, weight=ft.FontWeight.BOLD,
                                     color=_c('text_dim'))
        self._folder_icon  = ft.Icon(ft.Icons.FOLDER_OUTLINED, size=18, color=_c('accent'))
        self._folder_value = ft.Text(
            _t('folder_root'), size=13, color=_c('text_dim'), expand=True,
            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
        )
        self._folder_arrow = ft.Icon(ft.Icons.ARROW_DROP_DOWN_ROUNDED, size=22,
                                     color=_c('text_dim'))
        self._folder_box = ft.Container(
            content=ft.Row(
                [self._folder_icon, self._folder_value, self._folder_arrow],
                spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=40,
            bgcolor=_c('card_bg'),
            border=_border_all(1, _c('card_border')),
            border_radius=8,
            padding=ft.Padding(left=10, right=4, top=0, bottom=0),
            ink=True,
            on_click=self._open_folder_picker,
        )

        self._save_btn = ft.FilledButton(
            content=ft.Row(
                [ft.Icon(ft.Icons.SAVE_OUTLINED, color='#FFFFFF', size=16),
                 ft.Text(_t('save'), color='#FFFFFF', weight=ft.FontWeight.BOLD)],
                spacing=6, tight=True,
            ),
            on_click=self._save_variable,
            style=_btn_style(_c('success')),
        )

        # card 1: variable info = name + folder      card 2: the value, on its own
        self._editor_card = ft.Container(
            content=ft.Column(
                [
                    ft.Column([self._name_lbl,   self._name_inp],   spacing=4),
                    ft.Divider(height=1, color=_c('card_border')),
                    ft.Column([self._folder_lbl, self._folder_box], spacing=4),
                ],
                spacing=12,
            ),
            bgcolor=_c('card_bg'),
            border=_border_all(1, _c('card_border')),
            border_radius=12,
            padding=ft.Padding(left=14, right=14, top=12, bottom=12),
        )
        self._value_card = ft.Container(
            content=ft.Column([self._value_lbl, self._value_inp], spacing=4),
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
                                    ft.Text(_t('info_var'), size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=_c('text_dim')),
                                    self._editor_card,
                                    self._value_card,
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
        self._refresh_list_data(reset=True)      # list was re-mounted -> back to the top
        self._list_root.key     = "vars_list"
        self._container.content = self._list_root
        self._page.update()

    def _open_editor(self, var_path: str, folder_id: str = None):
        """folder_id: folder preselected for a NEW variable (default: the open folder)."""
        self._edit_path    = var_path
        self._current_view = 'editor'

        if not var_path:
            self._name_inp.value     = ''
            self._value_inp.value    = ''
            self._editor_title.value = _t('new_variable_file')
            self._folder_id          = (self._cur_folder if folder_id is None else folder_id) or ''
        else:
            var  = next((v for v in self._variables if v.get('_path') == var_path), {})
            name = var.get('name', '')
            self._name_inp.value     = name
            self._value_inp.value    = var.get('value', '')
            self._editor_title.value = _ar(f'{name}.json')
            self._folder_id          = var.get('folder', '') or ''

        self._refresh_folder_field()
        self._update_scoped_btn_visibility()
        self._clear_name_error()
        self._clear_dirty()

        self._editor_root.key   = f"vars_editor_{var_path or 'new'}"
        self._container.content = self._editor_root
        self._page.update()

    def _update_scoped_btn_visibility(self):
        name = (self._name_inp.value or '').strip()
        self._scoped_btn.visible = bool(name)

    def _refresh_list(self, reset: bool = False):
        self._refresh_list_data(reset=reset)
        self._page.update()

    def _refresh_list_data(self, reset: bool = False):
        """reset=True -> back to the top (search / re-mounted list / folder change);
        otherwise the user's scroll position is kept (poll, theme change, JSON editor close)."""
        if self._bot_dir:
            self._variables = _load_all_vars(self._bot_dir)
            self._ids_data  = _load_ids_data(self._bot_dir)
            self._folders   = _load_folders(self._bot_dir)
        if self._cur_folder and self._cur_folder not in self._folders:
            self._cur_folder = ''

        seen   = set()
        unique = []
        for v in self._variables:
            key = v.get('_path', id(v))
            if key not in seen:
                seen.add(key)
                unique.append(v)
        self._variables = unique

        q = (self._search_inp.value or '').strip().lower()
        if q:
            rows = []
            matches = [
                v for v in self._variables
                if q in (v.get('name')  or '').lower()
                or q in (v.get('value') or '').lower()
            ]
            for i, v in enumerate(matches, 1):
                r = dict(v)
                r.update(kind='var', num=i,
                         folder_path=_folder_path(self._folders, v.get('folder') or ''))
                rows.append(r)
        else:
            rows = _build_level_rows(self._variables, self._folders, self._cur_folder)

        self._update_crumbs(searching=bool(q))
        self._empty_lbl.visible = (len(rows) == 0)

        self._vlist.set_items(rows, reset=reset)

        self._update_vars_count()

    def _var_card(self, num: int, var: dict) -> ft.Control:
        if var.get('kind') == 'folder':
            return self._folder_row(var)
        num  = var.get('num', num)
        path = var.get('_path', '')
        name = var.get('name', '')
        sub_text = var.get('value', '') or '—'
        if var.get('folder_path'):
            sub_text = f"📁 {var['folder_path']}  •  {sub_text}"
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
                                            color=_c('text'),
                                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(_ar(sub_text), size=11,
                                            color=_c('text_dim'),
                                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.FilledButton(
                                content=ft.Text(_t('edit'),
                                                color=_c('text_on_accent')),
                                on_click=lambda _, p=path: self._open_editor(p),
                                style=_btn_style(
                                    _c('accent'),
                                    _c('text_on_accent'),
                                    ft.Padding(left=10, right=10, top=4, bottom=4),
                                ),
                            ),
                            ft.FilledButton(
                                content=ft.Text(_t('del'), color='#FFFFFF'),
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
                    height=self._ROW_H,
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
            on_confirm=lambda: self._do_delete(path, name),
        )

    def _do_delete(self, path: str, name: str):
        _delete_var(self._bot_dir, path, name)
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

        safe_name = _safe_name(name)

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
            self._bot_dir, name, value, self._edit_path, self._folder_id
        )
        self._cur_folder = self._folder_id          # list opens on the folder it was saved in

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

    # ── folders: navigation (drill-down with a breadcrumb bar) ───────────────
    def _enter_folder(self, fid: str):
        self._cur_folder = fid if fid in self._folders else ''
        self._refresh_list(reset=True)

    def _update_crumbs(self, searching: bool = False):
        chain, fid, seen = [], self._cur_folder, set()
        while fid and fid in self._folders and fid not in seen:
            seen.add(fid)
            chain.append(fid)
            fid = self._folders[fid]['parent']
        chain.reverse()

        def _chip(target: str, label: str, last: bool, icon=None) -> ft.Control:
            fg = _c('text_on_accent') if last else _c('text')
            parts = []
            if icon is not None:
                parts.append(ft.Icon(icon, size=16, color=fg))
            if label:
                parts.append(ft.Text(label, size=11, color=fg,
                                     weight=ft.FontWeight.BOLD if last else None,
                                     max_lines=1, overflow=ft.TextOverflow.ELLIPSIS))
            return ft.Container(
                content=ft.Row(parts, spacing=4, tight=True,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding(left=8, right=8, top=5, bottom=5),
                border_radius=14,
                bgcolor=_c('accent') if last else None,
                on_click=lambda _, i=target: self._enter_folder(i),
            )

        items = [_chip('', '', not chain, ft.Icons.HOME_ROUNDED)]
        for i, f in enumerate(chain):
            items.append(ft.Icon(ft.Icons.KEYBOARD_ARROW_RIGHT_ROUNDED, size=14,
                                 color=_c('text_dim')))
            items.append(_chip(f, self._folders[f]['name'], i == len(chain) - 1))
        self._crumbs.controls = items
        self._crumbs_box.visible = not searching

    def _folder_row(self, item: dict) -> ft.Control:
        fid = item['id']
        card = ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(_ar(item['name']), size=12,
                                    weight=ft.FontWeight.BOLD, color=_c('text'),
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(_t('folder_items').format(n=item.get('count', 0)),
                                    size=11, color=_c('text_dim')),
                        ],
                        spacing=2, expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.MORE_VERT_ROUNDED, icon_size=20,
                        icon_color=_c('text_dim'),
                        on_click=lambda _, i=fid: self._folder_menu(i),
                    ),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=_c('card_bg'),
            border=_border_all(1, _c('accent')),
            border_radius=10,
            padding=ft.Padding(left=10, right=4, top=4, bottom=4),
            height=self._ROW_H,
            expand=True,
            ink=True,
            on_click=lambda _, i=fid: self._enter_folder(i),
        )
        return ft.Row(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.FOLDER_ROUNDED, size=22, color=_c('accent')),
                    width=24, alignment=ft.Alignment(0, 0),
                ),
                card,
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # ── folders: actions ─────────────────────────────────────────────────
    def _toast(self, text: str):
        self._page.show_dialog(ft.SnackBar(
            content=ft.Text(text, color='#FFFFFF'),
            bgcolor=_c('danger'), duration=2500,
        ))

    def _create_folder_dialog(self, parent: str = ''):
        if not self._bot_dir:
            return

        def _ok(name: str):
            _create_folder(self._bot_dir, name, parent)
            self._refresh_list()

        _prompt_folder_name(
            self._page,
            _t('folder_new_sub') if parent else _t('folder_new'),
            '', _make_name_validator(self._bot_dir, parent), _ok,
        )

    def _folder_menu(self, fid: str):
        f = self._folders.get(fid)
        if not f:
            return

        def _item(icon, text, fn, color=None):
            col = color or _c('text')
            def _go(_):
                self._page.pop_dialog()
                fn()
            return ft.TextButton(
                content=ft.Row([ft.Icon(icon, size=18, color=col),
                                ft.Text(text, size=13, color=col)], spacing=10),
                on_click=_go,
            )

        self._page.show_dialog(ft.AlertDialog(
            modal=False,
            bgcolor=_c('card_bg'),
            shape=ft.RoundedRectangleBorder(radius=16),
            title=_dlg_title(ft.Icons.FOLDER_ROUNDED, f['name']),
            content=ft.Column(
                [
                    _item(ft.Icons.CREATE_NEW_FOLDER_OUTLINED, _t('folder_new_sub'),
                          lambda: self._create_folder_dialog(fid)),
                    _item(ft.Icons.NOTE_ADD_OUTLINED, _t('folder_new_var'),
                          lambda: self._open_editor('', fid)),
                    _item(ft.Icons.EDIT_OUTLINED, _t('folder_rename'),
                          lambda: self._rename_dialog(fid)),
                    _item(ft.Icons.DRIVE_FILE_MOVE_OUTLINED, _t('folder_move'),
                          lambda: self._move_dialog(fid)),
                    _item(ft.Icons.DELETE_OUTLINE_ROUNDED, _t('folder_delete'),
                          lambda: self._delete_folder_dialog(fid), _c('danger')),
                ],
                tight=True, spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            actions=[ft.TextButton(content=ft.Text(_t('cancel'), color=_c('text_dim')),
                                   on_click=lambda _: self._page.pop_dialog())],
            actions_alignment=ft.MainAxisAlignment.END,
        ))

    def _rename_dialog(self, fid: str):
        f = self._folders.get(fid)
        if not f:
            return

        def _ok(name: str):
            _rename_folder(self._bot_dir, fid, name)
            self._refresh_list()

        _prompt_folder_name(
            self._page, _t('folder_rename'), f['name'],
            _make_name_validator(self._bot_dir, f['parent'], exclude=fid), _ok,
        )

    def _move_dialog(self, fid: str):
        f = self._folders.get(fid)
        if not f:
            return

        def _picked(new_parent: str):
            if new_parent == f['parent']:
                return
            if _folder_name_taken(_load_folders(self._bot_dir), new_parent,
                                  f['name'], exclude=fid):
                self._toast(_t('folder_name_taken'))
                return
            if not _move_folder(self._bot_dir, fid, new_parent):
                self._toast(_t('folder_move_failed'))
                return
            self._refresh_list()

        _folder_picker(self._page, self._bot_dir, f['parent'], _picked,
                       exclude_root=fid)

    def _delete_folder_dialog(self, fid: str):
        f = self._folders.get(fid)
        if not f:
            return

        def _do():
            if self._cur_folder == fid:              # we are inside it -> go one level up
                self._cur_folder = f['parent']
            _delete_folder(self._bot_dir, fid)
            self._refresh_list()

        _confirm_folder_delete(self._page, f['name'], _do)

    # ── folders: editor field ────────────────────────────────────────────
    def _refresh_folder_field(self):
        folders = _load_folders(self._bot_dir) if self._bot_dir else {}
        if self._folder_id not in folders:
            self._folder_id = ''
        path = _folder_path(folders, self._folder_id)
        self._folder_value.value = path or _t('folder_root')
        self._folder_value.color = _c('text') if path else _c('text_dim')

    def _open_folder_picker(self, _=None):
        if not self._bot_dir:
            return

        def _picked(fid: str):
            self._folder_id = fid
            self._refresh_folder_field()
            self._mark_dirty()
            if self._page:
                self._page.update()

        _folder_picker(self._page, self._bot_dir, self._folder_id, _picked)

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
                    content=ft.Text(_t('cancel'), color=_c('text_dim')),
                    on_click=self._request_close_json_editor,
                ),
                ft.FilledButton(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.SAVE_OUTLINED, color='#FFFFFF', size=16),
                         ft.Text(_t('save'), color='#FFFFFF',
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

        u_dir = _user_vars_dir(self._bot_dir)
        g_dir = _guild_vars_dir(self._bot_dir)
        user_vars  = _load_scoped_var(u_dir, name)
        guild_vars = _load_scoped_var(g_dir, name)
        ids_data   = self._ids_data.get(name, {})

        data_to_show = {
            "user_vars": user_vars,
            "guild_vars": guild_vars,
            "ids_data": ids_data,
        }

        self._json_editor.value = json.dumps(data_to_show, ensure_ascii=False, indent=2)
        self._json_editor_title.value = _t('scoped_json_title').format(name=name)

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
            self._json_editor_error_lbl.value   = f'{_t("invalid_json")}: {e}'
            self._json_editor_error_lbl.visible = True
            self._page.update()
            return

        if not isinstance(parsed, dict):
            self._json_editor_error_lbl.value   = _t('json_must_be_object')
            self._json_editor_error_lbl.visible = True
            self._page.update()
            return

        if not self._bot_dir:
            print('[Variables] bot_dir not set')
            return

        name = self._json_editor_var
        u_dir = _user_vars_dir(self._bot_dir)
        g_dir = _guild_vars_dir(self._bot_dir)

        if any(k in parsed for k in ("user_vars", "guild_vars", "ids_data")):
            if "user_vars" in parsed and isinstance(parsed["user_vars"], dict):
                _save_scoped_var(u_dir, name, parsed["user_vars"])
            if "guild_vars" in parsed and isinstance(parsed["guild_vars"], dict):
                _save_scoped_var(g_dir, name, parsed["guild_vars"])
            if "ids_data" in parsed and isinstance(parsed["ids_data"], dict):
                self._ids_data = _load_ids_data(self._bot_dir)
                norm = {str(k): ('' if v is None else str(v)) for k, v in parsed["ids_data"].items()}
                if norm:
                    self._ids_data[name] = norm
                else:
                    self._ids_data.pop(name, None)
                _save_ids_data(self._bot_dir, self._ids_data)
        else:
            norm = {str(k): ('' if v is None else str(v)) for k, v in parsed.items()}
            has_colon = any(':' in k for k in norm.keys())
            if has_colon:
                _save_scoped_var(u_dir, name, norm)
            else:
                self._ids_data = _load_ids_data(self._bot_dir)
                if norm:
                    self._ids_data[name] = norm
                else:
                    self._ids_data.pop(name, None)
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