# main_app/core_fdsb/event_FDScripts/_event_scan.py

import os


def iter_event_files(events_dir: str):
    if not os.path.isdir(events_dir):
        return
    for fname in os.listdir(events_dir):
        fpath = os.path.join(events_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                script_text = f.read()
        except Exception as e:
            print(f"[EventScan Error] Failed to read {fname}: {e}")
            continue

        if not script_text.strip():
            continue

        first_line_norm = script_text.split('\n')[0].strip().replace(" ", "").lower()
        yield fname, script_text, first_line_norm


def extract_bracket_content(first_line_norm: str) -> str | None:
    try:
        return first_line_norm.split('[', 1)[1].rsplit(']', 1)[0]
    except IndexError:
        return None


def extract_words(first_line_norm: str) -> list[str]:
    inside = extract_bracket_content(first_line_norm)
    if not inside:
        return []
    return [w.strip() for w in inside.split(';') if w.strip()]