#!/usr/bin/env python3
import json, csv, argparse
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "logs"
LOG_FILE = LOG_DIR / "actions.jsonl"

def parse_ts(ts_ms: int) -> str:
    dt = datetime.fromtimestamp(ts_ms/1000, tz=timezone.utc).astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def load_events():
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

def export_csv(events):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    
    actions_path = LOG_DIR / "actions.csv"
    with actions_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts_ms","ts_local","action","card_id","title","status","priority","extra_json"])
        for e in events:
            w.writerow([
                e.get("ts_ms",""),
                parse_ts(int(e.get("ts_ms",0) or 0)) if e.get("ts_ms") else "",
                e.get("action",""),
                e.get("card_id",""),
                e.get("title",""),
                e.get("status",""),
                e.get("priority",""),
                json.dumps(e.get("extra", {}), ensure_ascii=False),
            ])

    
    standups_path = LOG_DIR / "standups.csv"
    with standups_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts_ms","ts_local","card_id","title","yesterday","today","blockers"])
        for e in events:
            if e.get("action") != "standup":
                continue
            w.writerow([
                e.get("ts_ms",""),
                parse_ts(int(e.get("ts_ms",0) or 0)) if e.get("ts_ms") else "",
                e.get("card_id",""),
                e.get("title",""),
                e.get("yesterday",""),
                e.get("today",""),
                e.get("blockers",""),
            ])

    
    imp_path = LOG_DIR / "impediments.csv"
    with imp_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts_ms","ts_local","card_id","title","status","priority"])
        for e in events:
            if e.get("action") != "imp":
                continue
            w.writerow([
                e.get("ts_ms",""),
                parse_ts(int(e.get("ts_ms",0) or 0)) if e.get("ts_ms") else "",
                e.get("card_id",""),
                e.get("title",""),
                e.get("status",""),
                e.get("priority",""),
            ])

    print("Exported CSV files:")
    print(f"- {actions_path}")
    print(f"- {standups_path}")
    print(f"- {imp_path}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="store_true", help="export CSVs into logs/")
    args = ap.parse_args()

    if not args.csv:
        print("Use: ./fb export --csv")
        return

    events = load_events()
    export_csv(events)

if __name__ == "__main__":
    main()
