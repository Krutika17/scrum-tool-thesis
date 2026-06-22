#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def run(cmd):
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)


def extract_id(output_text: str) -> str:
    """
    Extract created card id from command output that may include HTTP headers
    plus a JSON body.
    """
    m = re.search(r"(\{.*|\[.*)", output_text, re.DOTALL)
    body = m.group(1).strip() if m else output_text.strip()

    try:
        data = json.loads(body)
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            return data[0].get("id", "")
        if isinstance(data, dict):
            return data.get("id", "")
    except Exception:
        pass

    m2 = re.search(r'"id"\s*:\s*"([^"]+)"', body)
    return m2.group(1) if m2 else ""


def blockers_mean_none(text: str) -> bool:
    t = (text or "").strip().lower()
    none_values = {
        "",
        "none",
        "none as of now",
        "no",
        "no blockers",
        "n/a",
        "na",
        "nil",
        "-",
    }
    return t in none_values or t.startswith("none ")


def prompt_if_missing(value: str, prompt_text: str) -> str:
    if value and value.strip():
        return value.strip()
    return input(prompt_text).strip()


def main():
    ap = argparse.ArgumentParser(prog="fb_standup.py")
    ap.add_argument("--title", default="", help="optional standup card title")
    ap.add_argument("--yesterday", default="", help="what was done yesterday")
    ap.add_argument("--today", default="", help="what will be done today")
    ap.add_argument("--blockers", default="", help="blockers or none")
    args = ap.parse_args()

    today_str = datetime.now().strftime("%Y-%m-%d")
    standup_title = args.title.strip() or f"Standup — {today_str}"

    y = prompt_if_missing(args.yesterday, "Yesterday (what was done?): ")
    t = prompt_if_missing(args.today, "Today (what will be done?): ")
    b = prompt_if_missing(args.blockers, "Blockers (type 'none' if no blockers): ")

    # Create standup card
    out = run(
        [
            os.path.join(SCRIPT_DIR, "fb_add_v1.sh"),
            standup_title,
            "todo",
            "medium",
        ]
    )
    print(out)

    standup_id = extract_id(out)
    if not standup_id:
        print("ERROR: Could not extract standup card id from create response.", file=sys.stderr)
        sys.exit(1)

    # Add notes to the standup card
    run([os.path.join(SCRIPT_DIR, "fb_note.py"), standup_id, f"Yesterday: {y}"])
    run([os.path.join(SCRIPT_DIR, "fb_note.py"), standup_id, f"Today: {t}"])
    run([os.path.join(SCRIPT_DIR, "fb_note.py"), standup_id, f"Blockers: {b}"])

    # Log the standup
    run(
        [
            "python3",
            os.path.join(SCRIPT_DIR, "fb_log.py"),
            "standup",
            "--card",
            standup_id,
            "--title",
            standup_title,
            "--yesterday",
            y,
            "--today",
            t,
            "--blockers",
            b,
        ]
    )

    # Only create impediment when blockers are real
    if not blockers_mean_none(b):
        imp_out = run([os.path.join(SCRIPT_DIR, "fb.sh"), "imp", b])
        print(imp_out)

    print(f"Standup saved. card={standup_id}")


if __name__ == "__main__":
    main()