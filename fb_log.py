cat > fb_log.py <<'EOF'
#!/usr/bin/env python3
import json
import time
import sys
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_PATH = SCRIPT_DIR / "logs" / "actions.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def now_ms():
    return int(time.time() * 1000)

def parse_extra(extra):
    if extra is None or extra == "":
        return None
    if isinstance(extra, dict):
        return extra
    try:
        return json.loads(extra)
    except Exception:
        return {"raw": str(extra)}

def write_record(action: str, card_id: str = "", title: str = "", status: str = "", priority: str = "", extra=None):
    rec = {
        "ts_ms": now_ms(),
        "action": action,
        "card_id": card_id or "",
        "title": title or "",
        "status": status or "",
        "priority": priority or "",
    }

    parsed_extra = parse_extra(extra)
    if parsed_extra is not None:
        rec["extra"] = parsed_extra

    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def has_flag_args(argv):
    return any(arg.startswith("--") for arg in argv[2:])

def handle_positional(argv):
    action = argv[1] if len(argv) > 1 else ""
    card_id = argv[2] if len(argv) > 2 else ""
    title = argv[3] if len(argv) > 3 else ""
    status = argv[4] if len(argv) > 4 else ""
    priority = argv[5] if len(argv) > 5 else ""
    extra = argv[6] if len(argv) > 6 else ""

    if not action:
        print("Missing action", file=sys.stderr)
        sys.exit(2)

    write_record(action, card_id, title, status, priority, extra)
    print(f"LOGGED -> {LOG_PATH}")

def handle_flag_mode():
    ap = argparse.ArgumentParser(prog="fb_log.py")
    ap.add_argument("action")
    ap.add_argument("--card", dest="card_id", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--status", default="")
    ap.add_argument("--priority", default="")
    ap.add_argument("--extra", default="")
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

    write_record(
        action=args.action,
        card_id=args.card_id,
        title=args.title,
        status=args.status,
        priority=args.priority,
        extra=extra,
    )
    print(f"LOGGED -> {LOG_PATH}")

def main():
    if len(sys.argv) < 2:
        print("Missing action", file=sys.stderr)
        sys.exit(2)

    if has_flag_args(sys.argv):
        handle_flag_mode()
    else:
        handle_positional(sys.argv)

if __name__ == "__main__":
    main()
EOF

chmod +x fb_log.py
