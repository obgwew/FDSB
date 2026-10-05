# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/storage_ops.py

import json
import os

_VARS_DIR: str = ''

def set_vars_dir(path: str):
    global _VARS_DIR
    _VARS_DIR = path

def _load_data() -> dict:
    if not _VARS_DIR or not os.path.isdir(_VARS_DIR):
        return {}
    result = {}
    for fname in os.listdir(_VARS_DIR):
        if not fname.endswith('.json'):
            continue
        try:
            with open(os.path.join(_VARS_DIR, fname), 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'name' in data:
                result[data['name']] = data.get('value', '')
        except Exception:
            pass
    return result

def _save_data(data: dict):
    if not _VARS_DIR:
        return
    os.makedirs(_VARS_DIR, exist_ok=True)
    for name, value in data.items():
        safe = ''.join(c for c in name if c.isalnum() or c in ('-', '_')).strip() or 'var'
        path = os.path.join(_VARS_DIR, f'{safe}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'name': name, 'value': str(value)}, f, ensure_ascii=False, indent=2)

def _get_ids_data_dir() -> str:
    if not _VARS_DIR:
        return ''
    return os.path.join(os.path.dirname(_VARS_DIR), 'bot_ids')

def _get_ids_data_path() -> str:
    return os.path.join(_get_ids_data_dir(), 'ids_data.json')

def _load_ids_data() -> dict:
    path = _get_ids_data_path()
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_ids_data(data: dict):
    path = _get_ids_data_path()
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _get_user_vars_dir() -> str:
    if not _VARS_DIR:
        return ''
    return os.path.join(os.path.dirname(_VARS_DIR), 'user_vars')

def _get_guild_vars_dir() -> str:
    if not _VARS_DIR:
        return ''
    return os.path.join(os.path.dirname(_VARS_DIR), 'guild_vars')

def _safe_var_filename(name: str) -> str:
    safe = ''.join(c for c in name if c.isalnum() or c in ('-', '_')).strip() or 'var'
    return f'{safe}.json'

def _load_scoped_var(base_dir: str, name: str) -> dict:
    if not base_dir:
        return {}
    path = os.path.join(base_dir, _safe_var_filename(name))
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        values = data.get('values') if isinstance(data, dict) else None
        return values if isinstance(values, dict) else {}
    except Exception:
        return {}

def _save_scoped_var(base_dir: str, name: str, values: dict) -> None:
    if not base_dir:
        return
    os.makedirs(base_dir, exist_ok=True)
    path = os.path.join(base_dir, _safe_var_filename(name))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'name': name, 'values': values}, f, ensure_ascii=False, indent=2)

def _delete_scoped_key(base_dir: str, name: str, key: str) -> bool:
    values = _load_scoped_var(base_dir, name)
    if key not in values:
        return False
    del values[key]
    _save_scoped_var(base_dir, name, values)
    return True
