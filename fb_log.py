#!/usr/bin/env python3
import json, time, sys, argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_PATH = SCRIPT_DIR / "logs" / "actions.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def now_ms():
    return int(time.time() * 1000)

def write_record(action: str, card_id: str = "", title: str = "", status: str = "", priority: str = "", extra=None):
    rec = {
        "ts_ms": now_ms(),
        "action": action,
        "card_id": card_id or "",
        "title": title or "",
        "status": status or "",
        "priority": priority or "",
    }
    if extra is not None and extra != "":
        if isinstance(extra, dict):
            rec["extra"] = extra
        else:
            try:
                rec["extra"] = json.loads(extra)
            except Exception:
                rec["extra"] = {"raw": str(extra)}
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def main():
    # Backward compatible positional format:
    # ./fb_log.py <action> <card_id> "<title>" <status> <priority> [extra_json]
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-") and sys.argv[1] not in ("log",):
        action = sys.argv[1] if len(sys.argv) > 1 else ""
        card_id = sys.argv[2] if len(sys.argv) > 2 else ""
        title = sys.argv[3] if len(sys.argv) > 3 else ""
        status = sys.argv[4] if len(sys.argv) > 4 else ""
        priority = sys.argv[5] if len(sys.argv) > 5 else ""
        extra = sys.argv[6] if len(sys.argv) > 6 else ""
        if not action:
            print("Missing action", file=sys.stderr)
            sys.exit(2)
        write_record(action, card_id, title, status, priority, extra)
        print(f"LOGGED -> {LOG_PATH}")
        return

    ap = argparse.ArgumentParser(prog="fb_log.py")
    ap.add_argument("action", help="action name, e.g. add/todo/prog/move/done/delete/note/imp/standup")
    ap.add_argument("--card", dest="card_id", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--status", default="")
    ap.add_argument("--priority", default="")
    ap.add_argument("--extra", default="")
    # standup fields
    ap.add_argument("--yesterday", default="")
    ap.add_argument("--today", default="")
    ap.add_argument("--blockers", default="")
    args = ap.parse_args()

    extra = None
    if args.action == "standup":
        extra = {
            "yesterday": args.yesterday,
            "today": args.today,
            "blockers": args.blockers,
        }
    elif args.extra:
        extra = args.extra

    write_record(args.action, args.card_id, args.title, args.status, args.priority, extra)
    print(f"LOGGED -> {LOG_PATH}")

if __name__ == "__main__":
    main()