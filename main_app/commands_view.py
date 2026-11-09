# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/commands_view.py . Flet 0.85.2+ / flet-code-editor-dsl v0.4.0

import os
import re
import json
import uuid
import flet as ft
import asyncio

from flet_code_editor_dsl import (
    EditorRegex,
    HighlightRule,
    ErrorPattern,
    FoldRule,
    VerticalMode,
    ScrollMode,
)

from main_app.theme.theme_engine import ThemeEngine
from main_app.langs._translations import Translations
from main_app.settings_app import get_current_lang, is_mobile, get_syntax_highlighting, get_show_editor_stats

try:
    from main_app.core_fdsb.FDCore import (
        KNOWN_COMMANDS, CONTROL_FLOW_COMMANDS, FUNCTION_COMMANDS,
    )
except ImportError:
    KNOWN_COMMANDS = set()
    CONTROL_FLOW_COMMANDS = {
        "if", "elif", "else", "endif", "while", "endwhile", "for", "endfor",
        "break", "return", "and", "or", "onlyIf", "onlyAdmin", "log",
    }
    FUNCTION_COMMANDS = {"func", "endfunc", "call"}

from main_app.core_fdsb.Server import EVENT_PREFIXES

try:
    from main_app.core_fdsb.engine_FDScript.parse_utils import _ESCAPE_MAP as _ESCAPES
except ImportError:
    _ESCAPES = {'n': '\n', 's': ' ', 't': '\t', 'r': '\r', '\\': '\\'}


def _t(key: str) -> str:
    return Translations.get(key, get_current_lang())

def _wiki_lang() -> str:
    return (get_current_lang() or 'en').lstrip('_')

def _ar(text: str) -> str:
    return text

def _c(key: str) -> str:
    return ThemeEngine.hex(key)


def _is_mounted(ctrl) -> bool:
    if ctrl is None:
        return False
    try:
        return ctrl.page is not None
    except RuntimeError:
        return False


def _editor_font_family(page) -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = (
        os.path.join(here, '..', 'assets', _EDITOR_FONT_FILE),
        os.path.join(here, 'assets', _EDITOR_FONT_FILE),
        os.path.join(os.getcwd(), 'assets', _EDITOR_FONT_FILE),
    )
    if not any(os.path.isfile(p) for p in candidates):
        print(f'[Commands] editor font not found ({_EDITOR_FONT_FILE}), using fallback')
        return _EDITOR_FONT_FALLBACK if is_mobile() else 'Consolas'
    try:
        fonts = dict(getattr(page, 'fonts', None) or {})
        if _EDITOR_FONT_NAME not in fonts:
            fonts[_EDITOR_FONT_NAME] = _EDITOR_FONT_FILE
            page.fonts = fonts
    except Exception as ex:
        print(f'[Commands] font register failed: {ex}')
    return _EDITOR_FONT_NAME

_HL_FUNC_COLOR    = '#F1C40F'
_HL_FONT_SIZE     = 16
_HL_FONT_SIZE_DESKTOP = 17

_EDITOR_MIN_LINES = 15

_EDITOR_FONT_NAME = 'Roboto Mono'
_EDITOR_FONT_FILE = 'fonts/RobotoMono-Regular.ttf'
_EDITOR_FONT_FALLBACK = 'monospace'
_EDITOR_TRAILING_SPACE = 48.0

_EDITOR_DEBOUNCE_MS = 100
_SHOW_ERRORS = True

_SELECTION_MENU_ITEMS = ["cut", "copy", "paste", "select_all", "undo", "redo"]
_MAGNIFIER_SIZE   = 110.0
_MAGNIFIER_ZOOM   = 1.6
_SCROLL_MODE      = ScrollMode.EDITOR_FIRST

_UNDERLINE_UNKNOWN_DOLLAR = False

_FOLD_PAIRS = (
    ("if", "endif"),
    ("while", "endwhile"),
    ("for", "endfor"),
    ("func", "endfunc"),
)

_NAME_END  = r"(?![\w\u0080-\uFFFF])"
_NAME_BODY = r"[A-Za-z_][\w\u0080-\uFFFF]*"


def _min_editor_height(is_mob: bool) -> float:
    font_size = _HL_FONT_SIZE if is_mob else _HL_FONT_SIZE_DESKTOP
    return round(_EDITOR_MIN_LINES * font_size * 1.25 + 16.0)


def _safe_hex(key: str, default: str) -> str:
    try:
        value = ThemeEngine.hex(key)
        return value or default
    except Exception:
        return default


def _hl_colors_from(g) -> dict:
    base = g('success', '#2ECC71')
    return {
        'base':    base,
        'control': g('syntax_control_flow',  '#9B59B6'),
        'func':    g('syntax_func',          _HL_FUNC_COLOR),
        'known':   g('syntax_cmd',           '#3498DB'),
        'bracket': g('syntax_brackets',      '#FC2323'),
        'semi':    g('syntax_semicolon',     '#8A200D'),
        'comment': g('text_dim',             '#7F8C8D'),
        'string':  g('syntax_string',        base),
        'escape':  g('syntax_escape',        '#0E9AA7'),
    }


def _alt(words) -> str:
    return "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))

_RETURN_COMMANDS = {
    "return", "returnGuildChannelsID", "returnGuildEmojisID",
    "returnGuildRolesID", "returnGetReactions",
    "returnGuildBansID", "returnGuildUsersID", "returnBotGuildsID",
}

def _command_sets():
    control = set(CONTROL_FLOW_COMMANDS) | _RETURN_COMMANDS
    func    = set(FUNCTION_COMMANDS) - control
    known   = set(KNOWN_COMMANDS) - control - set(FUNCTION_COMMANDS)
    return control, func, known


def _dollar_rule(words, color):
    if not words:
        return None
    return HighlightRule(r"\$(?:" + _alt(words) + r")" + _NAME_END, color)


def _build_regex_rules(colors: dict) -> list:
    control, func, known = _command_sets()

    rules = [
        HighlightRule(r"#.*", colors['comment']),
        HighlightRule(r'"[^"\n]*"', colors['string']),
        HighlightRule(r"'[^'\n]*'", colors['string']),
    ]

    for words, key in ((control, 'control'), (func, 'func'), (known, 'known')):
        rule = _dollar_rule(words, colors[key])
        if rule:
            rules.append(rule)

    rules.append(HighlightRule(r";", colors['semi']))
    rules.append(HighlightRule(r"[\[\]]", colors['bracket']))
    rules.append(HighlightRule(
        r"\\[" + re.escape("".join(_ESCAPES)) + r"]",
        colors['escape'],
    ))
    return rules


def _build_error_rules() -> list:
    if not _SHOW_ERRORS:
        return []

    errors = [ErrorPattern(r'"[^"\n]*$', "Unterminated string")]

    if _UNDERLINE_UNKNOWN_DOLLAR:
        control, func, known = _command_sets()
        valid = control | func | known
        if valid:
            errors.append(ErrorPattern(
                r"\$(?!(?:" + _alt(valid) + r")" + _NAME_END + r")" + _NAME_BODY,
                "Unknown command",
            ))
    return errors


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

def _theme_unsub(cb):
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


NEW_FILE_TEMPLATE = '$syncMode\n\n'


def _safe_cmd_name(name: str) -> str:
    name = (name or '').strip().replace(' ', '_')
    safe = ''.join(c for c in name if c.isalnum() or c in ('-', '_'))
    return safe or 'command'


def _display_cmd_name(file_path: str) -> str:
    return os.path.splitext(os.path.basename(file_path))[0].replace('_', ' ')


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

def _split_cmd_header(raw: str):
    """Split a .fds file into (prefix, order, content, has_prefix_line, folder).
    The "#PREFIX:", "#ORDER:" and "#FOLDER:" header lines are never part of the
    content. #ORDER / #FOLDER may appear in any order after #PREFIX."""
    prefix, order, folder, has_prefix = '', None, '', False
    content = raw
    if content.startswith('#PREFIX:'):
        has_prefix = True
        nl      = content.find('\n')
        prefix  = content[8:nl].strip() if nl != -1 else content[8:].strip()
        content = content[nl + 1:] if nl != -1 else ''

    while True:
        if content.startswith('#ORDER:'):
            nl   = content.find('\n')
            head = content[7:nl] if nl != -1 else content[7:]
            try:
                n = int(head.strip())
            except ValueError:
                break
            order   = n
            content = content[nl + 1:] if nl != -1 else ''
        elif content.startswith('#FOLDER:'):
            nl      = content.find('\n')
            head    = content[8:nl] if nl != -1 else content[8:]
            folder  = head.strip()
            content = content[nl + 1:] if nl != -1 else ''
        else:
            break
    return prefix, order, content, has_prefix, folder

def _parse_cmd_file(path: str) -> dict:
    name = _display_cmd_name(path)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
    except Exception:
        return {'name': name, 'prefix': '', 'content': '', 'path': path,
                'order': None, 'folder': ''}

    prefix, order, content, _, folder = _split_cmd_header(raw)
    return {'name': name, 'prefix': prefix, 'content': content,
            'path': path, 'order': order, 'folder': folder}

def _parse_cmd_header(path: str) -> dict:
    name = _display_cmd_name(path)
    prefix, order, folder, has_header = '', None, '', False
    try:
        with open(path, 'r', encoding='utf-8') as f:
            head = f.readline() + f.readline() + f.readline()
        prefix, order, _c_, has_header, folder = _split_cmd_header(head)
    except Exception:
        pass
    return {'name': name, 'prefix': prefix, 'path': path,
            'order': order, 'folder': folder, '_has_header': has_header}

def _scan_cmd_entries(bot_dir: str) -> list:
    results = []

    for folder, is_event in [(_cmds_dir(bot_dir), False), (_events_dir(bot_dir), True)]:
        if not os.path.isdir(folder):
            continue
        try:
            with os.scandir(folder) as it:
                for entry in it:
                    if entry.is_file() and entry.name.endswith('.fds'):
                        parsed = _parse_cmd_header(entry.path)
                        parsed['is_event'] = is_event
                        results.append(parsed)
        except Exception:
            pass

    return results

def _cmd_write_order(path: str, n: int) -> bool:
    """Insert the "#ORDER:n" header line into an old file that has none."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
        if not raw.startswith('#PREFIX:'):
            return False
        nl = raw.find('\n')
        if nl == -1:
            raw += '\n'
            nl = len(raw) - 1
        raw = raw[:nl + 1] + f'#ORDER:{n}\n' + raw[nl + 1:]
        _atomic_write(path, raw)
        return True
    except Exception as e:
        print(f'[Commands] order write failed: {e}')
        return False

def _cmd_ensure_orders(bot_dir: str, items: list) -> list:
    """One-time numbering of files created before the order system existed."""
    existing_max = max((c['order'] for c in items if c.get('order') is not None),
                       default=0)
    legacy = [c for c in items if c.get('order') is None and c.get('_has_header')]
    if legacy:
        nums = _assign_missing_orders([c['path'] for c in legacy], existing_max)
        for c in legacy:
            if _cmd_write_order(c['path'], nums[c['path']]):
                c['order'] = nums[c['path']]
    return items

def _cmd_next_order(bot_dir: str) -> int:
    items = _cmd_ensure_orders(bot_dir, _scan_cmd_entries(bot_dir))
    return max((c['order'] for c in items if c.get('order') is not None),
               default=0) + 1

def _list_cmd_files(bot_dir: str) -> list:
    items = _cmd_ensure_orders(bot_dir, _scan_cmd_entries(bot_dir))
    # oldest first, newest last (by the creation number stored in the file)
    items.sort(key=lambda c: (c['order'] if c.get('order') is not None else 0,
                              c['name'].lower()))
    return items

def _cmd_file_exists(bot_dir: str, safe_name: str, exclude_path: str = '') -> bool:
    exclude_abs = os.path.abspath(exclude_path) if exclude_path else ''
    for folder in (_cmds_dir(bot_dir), _events_dir(bot_dir)):
        candidate = os.path.join(folder, f'{safe_name}.fds')
        if os.path.isfile(candidate) and os.path.abspath(candidate) != exclude_abs:
            return True
    return False

def _write_cmd_file(bot_dir: str, name: str, prefix: str,
                    content: str, old_path: str = '', folder: str = '') -> str:
    safe     = _safe_cmd_name(name)

    if _is_event_prefix(prefix):
        dest_dir = _ensure_events_dir(bot_dir)
        folder_label = 'bot_events'
    else:
        dest_dir = _ensure_cmds_dir(bot_dir)
        folder_label = 'bot_commands'

    new_path = os.path.join(dest_dir, f'{safe}.fds')

    # keep the creation number of an existing file (also on rename),
    # otherwise take the next one from the shared counter
    order = None
    for p in (old_path, new_path):
        if p and os.path.isfile(p):
            order = _parse_cmd_header(p).get('order')
            if order is not None:
                break
    if order is None:
        order = _cmd_next_order(bot_dir)

    _atomic_write(new_path, _compose_cmd(prefix, order, folder, content))

    if old_path and os.path.abspath(old_path) != os.path.abspath(new_path):
        if os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass

    print(f'[Commands] saved → {new_path}  ({folder_label})')
    return new_path

def _atomic_write(path: str, text: str):
    """Write to a temp file, then swap it in. A crash mid-write can no longer
    leave a half-written / empty command file (temp name never ends in .fds)."""
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.isfile(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise

def _remove_cmd_file(path: str):
    if os.path.isfile(path):
        try:
            os.remove(path)
            print(f'[Commands] deleted → {path}')
        except Exception as e:
            print(f'[Commands] delete error: {e}')

# ═════════════════════════════════════════════════════════════════════════
#  Folders
#  • Each command/event file keeps its folder in a header line "#FOLDER:<id>"
#    (written right after #PREFIX / #ORDER). Files themselves never move, so
#    the bot keeps loading them exactly as before.
#  • The folder tree (id → name / parent / creation number) is stored in one
#    small hidden file next to the commands: bot_commands/.folders.json
#    Folders nest to any depth (parent = another folder's id).
#  • Inside a folder, files are shown in creation order (#ORDER).
# ═════════════════════════════════════════════════════════════════════════
_FOLDERS_FILE = '.folders.json'
_INDENT_PX = 16
_MAX_INDENT_LEVELS = 6


def _compose_cmd(prefix: str, order: int, folder: str, content: str) -> str:
    head = f'#PREFIX:{prefix}\n#ORDER:{order}\n'
    if folder:
        head += f'#FOLDER:{folder}\n'
    return head + content

def _cmd_set_folder(path: str, folder_id: str) -> bool:
    """Rewrite only the #FOLDER header of an existing command file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
        prefix, order, content, has_prefix, _old = _split_cmd_header(raw)
        if not has_prefix or order is None:
            return False
        _atomic_write(path, _compose_cmd(prefix, order, folder_id, content))
        return True
    except Exception as e:
        print(f'[Commands] folder write failed: {e}')
        return False


def _folders_file(bot_dir: str) -> str:
    return os.path.join(_cmds_dir(bot_dir), _FOLDERS_FILE)

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
        _ensure_cmds_dir(bot_dir)
        _atomic_write(_folders_file(bot_dir),
                      json.dumps({'folders': folders}, ensure_ascii=False, indent=2))
        return True
    except Exception as e:
        print(f'[Commands] folders save failed: {e}')
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

def _delete_folder(bot_dir: str, fid: str) -> bool:
    """Delete only the folder: its files and sub-folders move up one level."""
    folders = _load_folders(bot_dir)
    if fid not in folders:
        return False
    parent = folders[fid]['parent']
    for c in _scan_cmd_entries(bot_dir):
        if c.get('folder') == fid:
            _cmd_set_folder(c['path'], parent)
    for f in folders.values():
        if f['parent'] == fid:
            f['parent'] = parent
    del folders[fid]
    return _save_folders(bot_dir, folders)

def _load_cmds_and_folders(bot_dir: str):
    return _list_cmd_files(bot_dir), _load_folders(bot_dir)

def _build_tree_rows(cmds: list, folders: dict, expanded: set) -> list:
    """Flatten the folder tree into display rows. Per level: sub-folders first
    (oldest first), then the commands in creation order (numbered 1..n)."""
    kids  = _folder_children(folders)
    files = {}
    for c in cmds:                          # cmds already sorted by #ORDER
        fid = c.get('folder') or ''
        if fid not in folders:
            fid = ''
        files.setdefault(fid, []).append(c)

    totals = {}
    def total(fid):
        if fid not in totals:
            totals[fid] = len(files.get(fid, [])) + sum(total(k) for k in kids.get(fid, []))
        return totals[fid]

    rows = []
    def emit(parent, depth):
        for fid in kids.get(parent, []):
            is_open = fid in expanded
            rows.append({'kind': 'folder', 'id': fid, 'name': folders[fid]['name'],
                         'depth': depth, 'open': is_open, 'count': total(fid)})
            if is_open:
                emit(fid, depth + 1)
        for n, c in enumerate(files.get(parent, []), 1):
            r = dict(c)
            r.update(kind='cmd', depth=depth, num=n)
            rows.append(r)

    emit('', 0)
    return rows


def _btn_style(bg: str, fg: str = '#FFFFFF',
               padding: ft.Padding = None) -> ft.ButtonStyle:
    style = ft.ButtonStyle(bgcolor=bg, color=fg)
    if padding:
        style.padding = padding
    return style

def _border_all(width: float, color: str) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)

def _scrollbar_theme() -> ft.Theme:
    return ft.Theme(
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_visibility=True,
            track_visibility=True,
            interactive=True,
            thickness=14,
            radius=7,
            min_thumb_length=56,
            thumb_color=_c('accent'),
            track_color=_c('card_border'),
        )
    )

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


class CommandEditorView:

    def __init__(self, page: ft.Page, on_back=None, on_saved=None, on_wiki_request=None):
        self._page     = page
        self._on_back  = on_back
        self._on_saved = on_saved
        self._on_wiki_request = on_wiki_request
        self._bot_dir  = ''
        self._cmd_path = ''
        self._folder_id = ''

        self._last_lines_count = 1
        self._body_col = None
        self._editor_area = None
        self._is_mobile = is_mobile()

        self._syntax_enabled = get_syntax_highlighting()
        self._stats_enabled = get_show_editor_stats()
        self._stats_strip = None

        self._is_dirty = False
        self._snapshot: dict = {}

        self._hl_colors = _hl_colors_from(_safe_hex)

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

        # Folder selector: looks like a field, opens the folder tree dialog
        self._folder_icon  = ft.Icon(ft.Icons.FOLDER_OUTLINED, size=18, color=_c('accent'))
        self._folder_label = ft.Text(_t('folder_label'), size=11, color=_c('text_dim'))
        self._folder_value = ft.Text(
            _t('folder_root'), size=12, color=_c('text_dim'), expand=True,
            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
        )
        self._folder_arrow = ft.Icon(ft.Icons.ARROW_DROP_DOWN_ROUNDED, size=22,
                                     color=_c('text_dim'))
        self._folder_box = ft.Container(
            content=ft.Row(
                [self._folder_icon, self._folder_label,
                 self._folder_value, self._folder_arrow],
                spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=40,
            bgcolor=_c('card_bg'),
            border=_border_all(1, _c('card_border')),
            border_radius=4,
            padding=ft.Padding(left=10, right=4, top=0, bottom=0),
            ink=True,
            on_click=self._open_folder_picker,
        )

        self._lines_lbl = ft.Text('0', size=11, weight=ft.FontWeight.BOLD, color=_c('text'))
        self._chars_lbl = ft.Text('0', size=11, weight=ft.FontWeight.BOLD, color=_c('text'))

        control_set = set(CONTROL_FLOW_COMMANDS)
        func_set    = set(FUNCTION_COMMANDS) - control_set
        known_set   = set(KNOWN_COMMANDS) - control_set - func_set
        openers_closers = control_set | func_set
        folds = [
            FoldRule(f'${a}', f'${b}')
            for a, b in _FOLD_PAIRS
            if a in openers_closers and b in openers_closers
        ]

        init_height = _min_editor_height(self._is_mobile)

        self._editor = EditorRegex(
            value='',
            rules=_build_regex_rules(self._hl_colors),
            error_rules=_build_error_rules(),
            highlight_scope="current_line",
            autocomplete=True,
            autocomplete_trigger="$",
            autocomplete_words=sorted(control_set | func_set | known_set),
            remember_suggestions=True,
            folds=folds,
            fold_by_indent=False,
            line_numbers=True,
            syntax_highlighting=self._syntax_enabled,
            show_errors=_SHOW_ERRORS,
            code_folding=True,
            wrap=False,
            vertical_mode=VerticalMode.UNLIMITED,
            min_lines=_EDITOR_MIN_LINES,
            max_lines=None,
            height=init_height,
            horizontal_scroll_padding=_EDITOR_TRAILING_SPACE,
            width_level=30,
            font_family=_editor_font_family(self._page),
            font_size=_HL_FONT_SIZE if self._is_mobile else _HL_FONT_SIZE_DESKTOP,
            default_color=self._hl_colors['base'],
            background_color=_c('card_bg'),
            debounce_ms=_EDITOR_DEBOUNCE_MS,
            on_change=self._on_code_change,
            selection_menu=True,                       
            selection_menu_items=_SELECTION_MENU_ITEMS,
            mobile_controls=False,
            cursor_pad=False,
            magnifier=None,                            
            magnifier_size=_MAGNIFIER_SIZE,
            magnifier_zoom=_MAGNIFIER_ZOOM,
            scroll_mode=_SCROLL_MODE,
        )

        self._title_text = ft.Text(
            _t('new_command_file'), size=13, weight=ft.FontWeight.BOLD, color=_c('text')
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

    def dispose(self):
        _theme_unsub(self._on_theme)

    def _update_syntax_mode(self):
        """Re-read the global setting (App Settings) and apply it to the editor."""
        self._syntax_enabled = get_syntax_highlighting()
        self._editor.syntax_highlighting = self._syntax_enabled
        if _is_mounted(self._editor):
            self._editor.update()

    def _set_name_error(self):
        self._name_field.error                = _t('name_required')
        self._name_field.border_color         = _c('danger')
        self._name_field.focused_border_color = _c('danger')

    def _set_name_taken_error(self):
        self._name_field.error                = _t('name_taken')
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
            'content': self._editor.value       or '',
            'folder':  self._folder_id,
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
            'content': self._editor.value       or '',
            'folder':  self._folder_id,
        }
        self._is_dirty          = False
        self._dirty_dot.visible = False

    def _open_wiki(self, _=None):
        cb = self._on_wiki_request
        if not cb:
            return
        try:
            result = cb()
        except Exception as ex:
            print(f"[Commands] wiki shortcut failed: {ex}")
            return
        if asyncio.iscoroutine(result):
            async def _await_cb():
                await result
            self._page.run_task(_await_cb)

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
        g = lambda k, default='#888888': data.get(k, default)

        for field in (self._name_field, self._prefix_field):
            field.border_color         = g('card_border')
            field.focused_border_color = g('syntax_cmd')
            field.bgcolor              = g('card_bg')
            field.cursor_color         = g('syntax_cmd')
            field.label_style          = ft.TextStyle(color=g('text_dim'), size=11)
            field.text_style           = ft.TextStyle(color=g('text'), size=12)

        self._folder_box.bgcolor        = g('card_bg')
        self._folder_box.border         = _border_all(1, g('card_border'))
        self._folder_icon.color         = g('accent')
        self._folder_label.color        = g('text_dim')
        self._folder_arrow.color        = g('text_dim')
        self._folder_value.color        = g('text') if self._folder_id else g('text_dim')
        self._lines_lbl.color           = g('text')
        self._chars_lbl.color           = g('text')
        self._title_text.color          = g('text')
        self._save_btn.style            = _btn_style(g('success'))
        self._dirty_dot.bgcolor         = g('warning')

        if self._name_field.error:
            err_color = g('danger', '#FC2323')
            self._name_field.border_color         = err_color
            self._name_field.focused_border_color = err_color

        self._hl_colors = _hl_colors_from(g)

        self._editor.rules            = _build_regex_rules(self._hl_colors)
        self._editor.default_color    = self._hl_colors['base']
        self._editor.background_color = g('card_bg')
        if _is_mounted(self._editor):
            self._editor.update()

    def build(self) -> ft.Control:
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

        # small horizontal strip: first thing inside the editor box
        self._stats_strip = stats_strip = ft.Container(
            visible=self._stats_enabled,
            content=ft.Row(
                [
                    _stat_inline(_t('total_lines'), self._lines_lbl),
                    _stat_inline(_t('total_text'),  self._chars_lbl),
                ],
                spacing=14,
                alignment=ft.MainAxisAlignment.END,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=10, right=10, top=2, bottom=2),
            border=ft.Border(bottom=ft.BorderSide(1, _c('card_border'))),
        )

        wiki_shortcut_btn = ft.IconButton(
            icon=ft.Icons.MENU_BOOK_ROUNDED,
            icon_color=_c('accent'),
            tooltip=_t('wiki_events_tooltip'),
            on_click=self._open_wiki,
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

        def _card(content: ft.Control) -> ft.Container:
            return ft.Container(
                content=content,
                bgcolor=_c('card_bg'),
                border=_border_all(1, _c('card_border')),
                border_radius=12,
                padding=ft.Padding(left=10, right=10, top=10, bottom=10),
            )

        # card 1: command info  = name + folder
        info_card = _card(ft.Column([self._name_field, self._folder_box], spacing=6))
        # card 2: command trigger = prefix (alone) + where it is stored
        trigger_card = _card(ft.Column([prefix_row, self._dest_indicator], spacing=6))

        cur_lines = (self._editor.value or '').count('\n') + 1
        if cur_lines < _EDITOR_MIN_LINES:
            init_h = _min_editor_height(self._is_mobile)
            self._editor.height = init_h
            self._editor.min_lines = _EDITOR_MIN_LINES
        else:
            init_h = None
            self._editor.height = None
            self._editor.min_lines = cur_lines

        self._editor_area = ft.Container(
            key="cmd_editor_area",
            content=self._editor,
            height=init_h,
            bgcolor=_c('card_bg'),
        )
        editor_box = ft.Container(
            content=ft.Column([stats_strip, self._editor_area], spacing=0),
            bgcolor=_c('card_bg'),
            border=_border_all(1, _c('card_border')),
            border_radius=10,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

        body_col = ft.Column(
            [
                ft.Text(_t('info_command'), size=11, weight=ft.FontWeight.BOLD, color=_c('text_dim')),
                info_card,
                ft.Text(_t('command_trigger'), size=11, weight=ft.FontWeight.BOLD, color=_c('text_dim')),
                trigger_card,
                ft.Text(_t('command_editor'), size=12, weight=ft.FontWeight.BOLD, color=_c('text')),
                editor_box,
                ft.Container(height=70),
            ],
            spacing=10,
            expand=True,
            scroll=ft.ScrollMode.ADAPTIVE,
        )
        self._body_col = body_col

        return ft.Column(
            [
                header,
                ft.Stack(
                    [
                        ft.Container(
                            content=body_col,
                            padding=ft.Padding(left=12, right=12, top=8, bottom=0),
                            expand=True,
                            theme=_scrollbar_theme(),
                            dark_theme=_scrollbar_theme(),
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

    @property
    def folder_id(self) -> str:
        return self._folder_id

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

    def _update_stats(self, value: str):
        if not self._stats_enabled:
            return
        lines = value.count('\n') + 1
        if lines != self._last_lines_count:
            self._last_lines_count = lines
            self._lines_lbl.value = str(lines)
            if _is_mounted(self._lines_lbl):
                self._lines_lbl.update()

        self._chars_lbl.value = str(len(value))
        if _is_mounted(self._chars_lbl):
            self._chars_lbl.update()

    def _update_editor_height(self, lines: int):
        changed = False

        if lines < _EDITOR_MIN_LINES:
            min_h = _min_editor_height(self._is_mobile)
            if self._editor.height != min_h:
                self._editor.height = min_h
                changed = True
            if self._editor_area and self._editor_area.height != min_h:
                self._editor_area.height = min_h
                changed = True
            if getattr(self._editor, 'min_lines', None) != _EDITOR_MIN_LINES:
                self._editor.min_lines = _EDITOR_MIN_LINES
                changed = True
        else:
            if self._editor.height is not None:
                self._editor.height = None
                changed = True
            if self._editor_area and self._editor_area.height is not None:
                self._editor_area.height = None
                changed = True
            if getattr(self._editor, 'min_lines', None) != lines:
                self._editor.min_lines = lines
                changed = True

        if changed:
            if self._editor_area and _is_mounted(self._editor_area):
                self._editor_area.update()
            if _is_mounted(self._editor):
                self._editor.update()

    def _on_code_change(self, e):
        data = getattr(e, 'data', None)
        ctrl_val = getattr(getattr(e, 'control', None), 'value', None)
        value = data if isinstance(data, str) else (ctrl_val if isinstance(ctrl_val, str) else (self._editor.value or ''))
        self._editor.value = value

        self._update_stats(value)
        self._update_editor_height(value.count('\n') + 1)

        if not self._is_dirty:
            self._is_dirty = True
            self._dirty_dot.visible = True
            if _is_mounted(self._dirty_dot):
                self._dirty_dot.update()

    def load(self, bot_dir: str, cmd_data: dict = None, folder_id: str = ''):
        self._bot_dir  = bot_dir
        self._cmd_path = cmd_data.get('path', '') if cmd_data else ''
        self._folder_id = (cmd_data.get('folder', '') if cmd_data else folder_id) or ''

        if cmd_data:
            self._name_field.value   = cmd_data.get('name', '')
            self._prefix_field.value = cmd_data.get('prefix', '')
            self._editor.value       = cmd_data.get('content', '')
            self._title_text.value   = _ar(cmd_data.get('name', 'command') + '.fds')
        else:
            self._name_field.value   = ''
            self._prefix_field.value = ''
            self._editor.value       = NEW_FILE_TEMPLATE
            self._title_text.value   = _t('new_command_file')

        self._clear_name_error()

        content = self._editor.value or ''
        lines   = content.count('\n') + 1
        self._last_lines_count = lines

        if lines < _EDITOR_MIN_LINES:
            min_h = _min_editor_height(self._is_mobile)
            self._editor.min_lines = _EDITOR_MIN_LINES
            self._editor.height    = min_h
            if self._editor_area:
                self._editor_area.height = min_h
        else:
            self._editor.min_lines = lines
            self._editor.height    = None
            if self._editor_area:
                self._editor_area.height = None

        self._lines_lbl.value = str(lines)
        self._chars_lbl.value = str(len(content))

        self._refresh_folder_field()
        self._update_dest_indicator((self._prefix_field.value or '').strip())
        self._clear_dirty()

        self._syntax_enabled = get_syntax_highlighting()
        self._editor.syntax_highlighting = self._syntax_enabled

        self._stats_enabled = get_show_editor_stats()
        if self._stats_strip is not None:
            self._stats_strip.visible = self._stats_enabled
            if _is_mounted(self._stats_strip):
                self._stats_strip.update()


    def _save(self, _) -> bool:
        name    = (self._name_field.value or '').strip()
        prefix  = (self._prefix_field.value or '').strip()
        content = self._editor.value or ''

        if not name:
            self._set_name_error()
            if self._page:
                self._page.update()
            self._scroll_to_name_error()
            return False

        safe_name = _safe_cmd_name(name)

        if _cmd_file_exists(self._bot_dir, safe_name, self._cmd_path):
            self._set_name_taken_error()
            if self._page:
                self._page.update()
            self._scroll_to_name_error()
            return False

        self._clear_name_error()

        try:
            self._cmd_path = _write_cmd_file(
                self._bot_dir, name, prefix, content, self._cmd_path, self._folder_id
            )
        except Exception as ex:
            print(f'[Commands] save failed: {ex}')
            if self._page:
                self._page.show_dialog(
                    ft.SnackBar(
                        content=ft.Text(str(ex), color='#FFFFFF'),
                        bgcolor=_c('danger'),
                        duration=3000,
                    )
                )
                self._page.update()
            return False

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
        if self._is_mounted():             # not mounted yet -> nothing to clear
            lv.update()

    def _is_mounted(self) -> bool:
        """True only while the list is registered in the live Flet session.
        Calling a method on a control that is not registered (e.g. the editor
        is open in its place) makes the client answer for an unknown control
        ID; Flet then drops the connection and the whole app restarts."""
        try:
            return self.control._i in self._page.session.index
        except Exception:
            return False

    def _scroll_to(self, offset: float):
        if not self._is_mounted():
            # nothing to scroll: a re-mounted list starts at the top anyway
            self._scroll_pix = offset
            self._last_pix = offset
            return

        self._resetting = True

        async def _go():
            try:
                for _ in range(5):
                    if not self._is_mounted():
                        break
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
                if self._move_window(pix, self._scroll_view) and self._is_mounted():
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


class CommandsListView:
    _ROW_H = 58      # fixed row height -> exact scroll maths for the windowed list
    _GAP   = 10

    def __init__(self, page: ft.Page, on_open=None):
        self._page     = page
        self._on_open  = on_open
        self._bot_dir  = ''
        self._all_cmds = []
        self._folders  = {}
        self._expanded = set()
        self._busy     = False

        self._count_label = ft.Text(
            value="",
            size=11,
            color=_c('text_dim'),
        )

        self._search_field = ft.TextField(
            hint_text=_t('search'),
            height=40,
            width=150,
            content_padding=ft.Padding(left=10, right=10, top=0, bottom=0),
            bgcolor=_c('card_bg'),
            border_color=_c('card_border'),
            border_radius=8,
            enable_suggestions=True,
            on_change=self._on_search,
        )
        # Windowed list: only ~12-24 rows exist at any time, however many commands there are.
        self._vlist    = _VirtualList(page, self._cmd_row, item_height=self._ROW_H,
                                     gap=self._GAP, bottom_pad=60)
        self._list_col = self._vlist.control
        self._search_task = None

        ThemeEngine.subscribe(self._on_theme)

    def dispose(self):
        self._vlist.dispose()
        if self._search_task:
            self._search_task.cancel()
            self._search_task = None
        _theme_unsub(self._on_theme)

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
            self._render()
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
                            ft.IconButton(
                                icon=ft.Icons.CREATE_NEW_FOLDER_OUTLINED,
                                icon_color=_c('accent'), icon_size=22,
                                tooltip=_t('folder_new'),
                                on_click=lambda _: self._create_folder_dialog(''),
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

    def load(self, bot_dir: str, show_loading: bool = True, reset: bool = True):
        self._bot_dir  = bot_dir
        if show_loading or not self._all_cmds:
            self._vlist.show_message(
                ft.Container(
                    content=ft.ProgressRing(color=_c('accent')),
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding(0, 40, 0, 0)
                )
            )
            self._count_label.value = _t('loading')
            if self._page:
                self._page.update()

        self._page.run_task(self._async_load_task, reset)

    async def _async_load_task(self, reset=True):
        loop = asyncio.get_event_loop()
        self._all_cmds, self._folders = await loop.run_in_executor(
            None, _load_cmds_and_folders, self._bot_dir)
        self._render(reset=bool(reset))

    def _filtered(self) -> list:
        q = (self._search_field.value or '').strip().lower()
        if not q:
            return self._all_cmds
        return [
            c for c in self._all_cmds
            if q in c['name'].lower() or q in c['prefix'].lower()
        ]

    def _on_search(self, e):
        if self._search_task:
            self._search_task.cancel()

        async def _debounced():
            await asyncio.sleep(0.15)
            self._render(reset=True)

        self._search_task = self._page.run_task(_debounced)

    def _rows(self) -> list:
        """Search -> flat list of matches (with their folder path); otherwise the
        folder tree with only the expanded folders opened."""
        if (self._search_field.value or '').strip():
            out = []
            for i, c in enumerate(self._filtered(), 1):
                r = dict(c)
                r.update(kind='cmd', depth=0, num=i,
                         folder_path=_folder_path(self._folders, c.get('folder') or ''))
                out.append(r)
            return out
        return _build_tree_rows(self._all_cmds, self._folders, self._expanded)

    def _render(self, reset: bool = False):
        """reset=True -> back to the top (search / fresh load); otherwise the
        user's scroll position is kept (theme change, delete, expand/collapse)."""
        rows = self._rows()
        if not rows:
            self._vlist.show_message(
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
            self._vlist.set_items(rows, reset=reset)

        self._update_cmds_count()
        if self._page:
            self._page.update()

    def _cmd_row(self, num: int, cmd: dict) -> ft.Control:
        if cmd.get('kind') == 'folder':
            return self._folder_row(cmd)
        num    = cmd.get('num', num)
        indent = min(cmd.get('depth', 0), _MAX_INDENT_LEVELS) * _INDENT_PX
        sub_text = cmd['prefix'] or '—'
        if cmd.get('folder_path'):
            sub_text = f"📁 {cmd['folder_path']}  •  {sub_text}"
        is_event = cmd.get('is_event', False)

        name_row = ft.Row(
            [
                ft.Text(_ar(cmd['name']), size=12,
                        weight=ft.FontWeight.BOLD,
                        color=_c('text'),
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                        expand_loose=True),
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
                ft.Container(width=indent, visible=indent > 0),
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
                                    ft.Text(_ar(sub_text), size=11,
                                            color=_c('text_dim'),
                                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
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
                    height=self._ROW_H,
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
        self._all_cmds = [c for c in self._all_cmds if c.get('path') != cmd.get('path')]
        self._render()

    def _folder_row(self, item: dict) -> ft.Control:
        fid     = item['id']
        indent  = min(item.get('depth', 0), _MAX_INDENT_LEVELS) * _INDENT_PX
        is_open = item.get('open', False)

        card = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED if is_open
                        else ft.Icons.KEYBOARD_ARROW_RIGHT_ROUNDED,
                        size=20, color=_c('text_dim'),
                    ),
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
            on_click=lambda _, i=fid: self._toggle_folder(i),
        )
        return ft.Row(
            [
                ft.Container(width=indent, visible=indent > 0),
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.FOLDER_OPEN_ROUNDED if is_open else ft.Icons.FOLDER_ROUNDED,
                        size=22, color=_c('accent')),
                    width=24, alignment=ft.Alignment(0, 0),
                ),
                card,
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # ── folder actions ───────────────────────────────────────────────────
    def reveal_folder(self, fid: str):
        """Expand a folder and all of its parents (used after saving a command)."""
        folders = _load_folders(self._bot_dir) if self._bot_dir else {}
        seen = set()
        while fid and fid in folders and fid not in seen:
            seen.add(fid)
            self._expanded.add(fid)
            fid = folders[fid]['parent']

    def _toggle_folder(self, fid: str):
        if fid in self._expanded:
            self._expanded.discard(fid)
        else:
            self._expanded.add(fid)
        self._render()

    def _reload_folders(self):
        self._folders = _load_folders(self._bot_dir)
        self._render()

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
            if parent:
                self._expanded.add(parent)
            self._reload_folders()

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
                    _item(ft.Icons.NOTE_ADD_OUTLINED, _t('folder_new_cmd'),
                          lambda: self._open_new_in(fid)),
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

    def _open_new_in(self, fid: str):
        self._expanded.add(fid)
        if self._on_open:
            self._on_open(None, fid)

    def _rename_dialog(self, fid: str):
        f = self._folders.get(fid)
        if not f:
            return

        def _ok(name: str):
            _rename_folder(self._bot_dir, fid, name)
            self._reload_folders()

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
            if new_parent:
                self._expanded.add(new_parent)
            self._reload_folders()

        _folder_picker(self._page, self._bot_dir, f['parent'], _picked,
                       exclude_root=fid)

    def _delete_folder_dialog(self, fid: str):
        f = self._folders.get(fid)
        if not f:
            return

        def _do():
            _delete_folder(self._bot_dir, fid)
            self._expanded.discard(fid)
            self.load(self._bot_dir, show_loading=False, reset=False)

        _confirm_folder_delete(self._page, f['name'], _do)


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
            on_wiki_request=self._request_wiki_events,
        )

        self._container = ft.Container(content=None, expand=True)
        self._list_content = None

    def set_wiki_events_callback(self, callback):
        self._on_wiki_events_req = callback

    def _request_wiki_events(self):
        cb = self._on_wiki_events_req
        return cb() if cb else None

    def _list_ui(self, *args) -> ft.Control:
        if self._list_content is None:
            self._list_content = self._list_view.build()
            self._list_content.key = "cmds_list"
        return self._list_content

    def dispose(self):
        self._list_view.dispose()
        self._editor_view.dispose()

    def swipe_blocked(self) -> bool:
        return self._in_editor

    def handle_back(self) -> bool:
        if self._in_editor:
            self._editor_view.guard_navigation(self._close_editor)
            return True
        return False

    def on_show(self):
        if not self._in_editor and self._bot_dir and not self._list_view._all_cmds:
            self._list_view.load(self._bot_dir, show_loading=True)

    def on_hide(self):
        pass

    def _on_editor_saved(self):
        self._list_view.reveal_folder(self._editor_view.folder_id)
        self._list_view.load(self._bot_dir, show_loading=False)

    def build(self) -> ft.Control:
        content = self._list_ui()
        self._container.content = content
        return self._container

    def load_bot(self, bot_dir: str):
        self._bot_dir   = bot_dir
        self._in_editor = False
        self._list_view.load(bot_dir, show_loading=True)
        content = self._list_ui()
        self._container.content = content
        if self._page:
            self._page.update()

    def _open_editor(self, cmd_data=None, folder_id: str = ''):
        if cmd_data and 'content' not in cmd_data:
            full = _parse_cmd_file(cmd_data['path'])
            full['is_event'] = cmd_data.get('is_event', False)
            cmd_data = full
        self._in_editor = True
        self._editor_view.load(self._bot_dir, cmd_data, folder_id)
        content = self._editor_view.build()
        content.key = "cmd_editor"
        self._container.content = content
        if self._page:
            self._page.update()

    def _close_editor(self):
        self._in_editor = False
        content = self._list_ui()
        self._container.content = content
        if self._page:
            self._page.update()

    def guard_tab_change(self, on_proceed: callable, on_cancel: callable = None):
        def _reset_then_proceed():
            self._in_editor = False
            content = self._list_ui()
            self._container.content = content
            if self._page:
                self._page.update()
            on_proceed and on_proceed()

        if self._in_editor and self._editor_view.is_dirty:
            self._editor_view.guard_navigation(_reset_then_proceed, on_cancel)
        else:
            _reset_then_proceed()


def _stat_inline(heading: str, value_ctrl: ft.Text) -> ft.Row:
    return ft.Row(
        [
            ft.Text(heading, size=10, weight=ft.FontWeight.BOLD, color=_c('text_dim')),
            value_ctrl,
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )