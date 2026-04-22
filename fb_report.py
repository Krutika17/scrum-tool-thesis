#!/usr/bin/env python3
import argparse, json, os
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "logs"
LOG_FILE = LOG_DIR / "actions.jsonl"

def read_events():
    if not LOG_FILE.exists():
        return []
    events = []
    for line in LOG_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except Exception:
            pass
    return events

def ts_to_str(ts_ms: int) -> str:
    try:
        return datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "?"

def cmd_export_csv(kind: str, out_path: Path, events):
    import csv
    rows = []

    if kind == "activity":
        for e in events:
            rows.append({
                "ts": ts_to_str(e.get("ts_ms", 0)),
                "ts_ms": e.get("ts_ms", ""),
                "action": e.get("action", ""),
                "card_id": e.get("card_id", ""),
                "title": e.get("title", ""),
                "status": e.get("status", ""),
                "priority": e.get("priority", ""),
            })
        headers = ["ts","ts_ms","action","card_id","title","status","priority"]

    elif kind == "standup":
        for e in events:
            if e.get("action") != "standup":
                continue
            rows.append({
                "ts": ts_to_str(e.get("ts_ms", 0)),
                "ts_ms": e.get("ts_ms", ""),
                "card_id": e.get("card_id", ""),
                "title": e.get("title", ""),
                "yesterday": e.get("yesterday", ""),
                "today": e.get("today", ""),
                "blockers": e.get("blockers", ""),
            })
        headers = ["ts","ts_ms","card_id","title","yesterday","today","blockers"]

    elif kind == "impediments":
        for e in events:
            if e.get("action") != "imp":
                continue
            rows.append({
                "ts": ts_to_str(e.get("ts_ms", 0)),
                "ts_ms": e.get("ts_ms", ""),
                "card_id": e.get("card_id", ""),
                "title": e.get("title", ""),
                "status": "OPEN",  # from logs we treat imp as open unless you later add resolve
            })
        headers = ["ts","ts_ms","card_id","title","status"]

    else:
        raise SystemExit(f"Unknown export kind: {kind}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"CSV written: {out_path}")

def main():
    ap = argparse.ArgumentParser(prog="fb_report.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rep = sub.add_parser("activity", help="print recent activity from logs")
    rep.add_argument("--last", type=int, default=10)

    st = sub.add_parser("standup", help="print standup history from logs")
    st.add_argument("--last", type=int, default=7)

    imp = sub.add_parser("impediments", help="print impediments from logs")
    imp.add_argument("--open", action="store_true", default=False)

    today = sub.add_parser("today", help="print today's activity from logs")

    exp = sub.add_parser("export", help="export CSV from logs")
    exp.add_argument("--csv", action="store_true", default=True)
    exp.add_argument("--type", choices=["activity","standup","impediments"], default="activity")
    exp.add_argument("--out", default="", help="optional output path; default goes to logs/exports/...")

    args = ap.parse_args()
    events = read_events()

    if args.cmd == "activity":
        print("\nRecent activity (from logs)\n")
        for e in events[-args.last:]:
            print(f"- {ts_to_str(e.get('ts_ms',0))}  |  {e.get('action',''):<9}  |  card={e.get('card_id','')}  |  {e.get('title','')}")
        return

    if args.cmd == "standup":
        stands = [e for e in events if e.get("action") == "standup"]
        stands = stands[-args.last:]
        print("\nStandup history\n")
        for e in stands:
            print(f"- {ts_to_str(e.get('ts_ms',0))}  |  {e.get('title','')}  |  card={e.get('card_id','')}")
            print(f"  yesterday: {e.get('yesterday','')}")
            print(f"  today:     {e.get('today','')}")
            print(f"  blockers:  {e.get('blockers','')}\n")
        return

    if args.cmd == "impediments":
        imps = [e for e in events if e.get("action") == "imp"]
        print("\nImpediments (from logs)\n")
        for e in imps:
            print(f"- {ts_to_str(e.get('ts_ms',0))}  |  OPEN    |  {e.get('title','')}  |  card={e.get('card_id','')}")
        return

    if args.cmd == "today":
        today_str = datetime.now().strftime("%Y-%m-%d")
        print("\nToday activity (from logs)\n")
        for e in events:
            ts = ts_to_str(e.get("ts_ms",0))
            if ts.startswith(today_str):
                print(f"- {ts}  |  {e.get('action',''):<9}  |  card={e.get('card_id','')}  |  {e.get('title','')}")
        return

    if args.cmd == "export":
        kind = args.type
        if args.out.strip():
            out_path = Path(args.out).expanduser()
        else:
            out_dir = LOG_DIR / "exports"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{kind}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        cmd_export_csv(kind, out_path, events)
        return

if __name__ == "__main__":
    main()