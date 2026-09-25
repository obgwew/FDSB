# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later
# -*- coding: utf-8 -*-

# main_app/core_fdsb/server_FDScript/prefix_manager.py

import os


class PrefixManager:
    def __init__(self):
        self._bot_commands_dir = ''
        self._bot_events_dir = ''

    def set_bot_dir(self, bot_dir: str):
        abs_dir = os.path.abspath(bot_dir)
        if os.path.basename(abs_dir).lower() == 'bot_files':
            bot_root = os.path.dirname(abs_dir)
        else:
            bot_root = abs_dir
        self._bot_commands_dir = os.path.join(bot_root, 'bot_commands')
        self._bot_events_dir = os.path.join(bot_root, 'bot_events')

    def get_event_scripts(self, event_name: str) -> list[str]:
        results: list[tuple[float, str]] = []
        if not os.path.isdir(self._bot_events_dir):
            return []
        
        for fname in os.listdir(self._bot_events_dir):
            fpath = os.path.join(self._bot_events_dir, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not content.strip():
                    continue
                first_line = content.split('\n')[0].strip().replace(" ", "").upper()
                if first_line.startswith("#PREFIX:"):
                    prefix_part = first_line.replace("#PREFIX:", "").split('[')[0]
                    if prefix_part == event_name.upper():
                        try:
                            ctime = os.path.getctime(fpath)
                        except Exception:
                            ctime = os.path.getmtime(fpath)
                        results.append((ctime, content))
            except Exception:
                pass
        
        results.sort(key=lambda x: x[0])
        return [item[1] for item in results]

    def get_event_scripts_with_arg(self, event_name: str) -> list[tuple[str, str | None]]:
        results: list[tuple[float, str, str | None]] = []
        if not os.path.isdir(self._bot_events_dir):
            return []
        
        for fname in os.listdir(self._bot_events_dir):
            fpath = os.path.join(self._bot_events_dir, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not content.strip():
                    continue
                raw_first_line = content.split('\n')[0].strip()
                if raw_first_line.upper().startswith("#PREFIX:"):
                    prefix_body = raw_first_line.split(":", 1)[1].strip()
                    bstart = prefix_body.find('[')
                    bend = prefix_body.rfind(']')
                    prefix_name = (prefix_body[:bstart] if bstart != -1 else prefix_body).strip().upper()
                    if prefix_name == event_name.upper():
                        arg = None
                        if bstart != -1 and bend != -1 and bend > bstart:
                            arg = prefix_body[bstart + 1:bend].strip()
                        try:
                            ctime = os.path.getctime(fpath)
                        except Exception:
                            ctime = os.path.getmtime(fpath)
                        results.append((ctime, content, arg))
            except Exception:
                pass
        
        results.sort(key=lambda x: x[0])
        return [(item[1], item[2]) for item in results]

    def get_scripts_by_message(self, message_content: str) -> list[str]:
        if not os.path.isdir(self._bot_commands_dir):
            return []

        clean_msg = message_content.strip()
        matched_entries: list[tuple[float, str]] = []

        for fname in os.listdir(self._bot_commands_dir):
            fpath = os.path.join(self._bot_commands_dir, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.strip():
                    continue

                first_line = content.split('\n')[0].strip()
                if first_line.upper().startswith("#PREFIX:"):
                    prefix = first_line.split(":", 1)[1].strip()
                    if not prefix:
                        continue
                    
                    if clean_msg.startswith(prefix):
                        after = clean_msg[len(prefix):]
                        if not after or after[0].isspace():
                            try:
                                ctime = os.path.getctime(fpath)
                            except Exception:
                                ctime = os.path.getmtime(fpath)
                            
                            matched_entries.append((ctime, content))
            except Exception:
                pass

        matched_entries.sort(key=lambda x: x[0])

        return [item[1] for item in matched_entries]

    def get_script_by_message(self, message_content: str) -> str | None:
        scripts = self.get_scripts_by_message(message_content)
        return scripts[0] if scripts else None


prefix_manager = PrefixManager()