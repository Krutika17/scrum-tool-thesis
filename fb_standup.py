#!/usr/bin/env python3
import os, sys, subprocess
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run(cmd):
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)

def main():
    d = date.today().isoformat()
    title = f"Standup — {d}"

    print("Yesterday (what was done?): ", end="")
    y = input().strip()
    print("Today (what will be done?): ", end="")
    t = input().strip()
    print("Blockers (type 'none' if no blockers): ", end="")
    b = input().strip()

    
    out = run([os.path.join(SCRIPT_DIR, "fb_add_v1.sh"), title, "todo", "medium"])
    
    standup_id = ""
    for token in out.split('"id":"')[1:2]:
        standup_id = token.split('"', 1)[0]
    if not standup_id:
        standup_id = "unknown"

    
    run([os.path.join(SCRIPT_DIR, "fb_note.py"), standup_id, f"Yesterday: {y}"])
    run([os.path.join(SCRIPT_DIR, "fb_note.py"), standup_id, f"Today: {t}"])
    run([os.path.join(SCRIPT_DIR, "fb_note.py"), standup_id, f"Blockers: {b}"])

    
    try:
        run(["python3", os.path.join(SCRIPT_DIR, "fb_log.py"),
             "standup",
             "--card", standup_id,
             "--title", title,
             "--yesterday", y,
             "--today", t,
             "--blockers", b])
    except Exception:
        pass

    
    if b and b.lower() != "none":
        try:
            run([os.path.join(SCRIPT_DIR, "fb.sh"), "imp", b])
        except Exception:
            pass

    print('{"ok": true, "standup_card_id": "%s", "title": "%s"}' % (standup_id, title))

if __name__ == "__main__":
    main()
