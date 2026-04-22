#!/usr/bin/env python3
import os, sys, json, time
import argparse
import urllib.request

def die(msg: str, code: int = 2):
    print(msg, file=sys.stderr)
    sys.exit(code)

def env(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        die(f"Missing env var: '{name}'")
    return v

def http_json(method: str, url: str, token: str, data_obj=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": os.getenv("FOCALBOARD_URL", "http://localhost:8000").rstrip("/") + "/",
    }
    body = None
    if data_obj is not None:
        body = json.dumps(data_obj).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8")
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        return e.code, raw
    except Exception as e:
        die(f"HTTP error: {e}")

def pick_prop_ids(board_json):
    # Build lookup maps from board cardProperties
    status_prop = os.getenv("STATUS_PROP_ID", "")
    prio_prop = os.getenv("PRIORITY_PROP_ID", "")

    status_opt = {}
    prio_opt = {}

    cps = board_json.get("cardProperties", []) or []
    for p in cps:
        if p.get("type") != "select":
            continue
        pid = p.get("id")
        if pid == status_prop:
            for o in p.get("options", []):
                status_opt[o["id"]] = o.get("value", o["id"])
        if pid == prio_prop:
            for o in p.get("options", []):
                prio_opt[o["id"]] = o.get("value", o["id"])

    return status_prop, prio_prop, status_opt, prio_opt

def main():
    ap = argparse.ArgumentParser(prog="fb_list.py")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--status", choices=["todo","progress","done"], default=None)
    ap.add_argument("--priority", choices=["high","medium","low"], default=None)
    ap.add_argument("--query", default=None, help="substring match on title")
    args = ap.parse_args()

    base = os.getenv("FOCALBOARD_URL", "http://localhost:8000").strip().rstrip("/")

    token = env("FOCALBOARD_TOKEN")
    board_id = env("BOARD_ID")

    # Fetch board to map option IDs -> labels
    st, board = http_json("GET", f"{base}/api/v2/boards/{board_id}", token)
    if st != 200 or not isinstance(board, dict):
        die(f"Failed to get board ({st}): {board}")

    status_prop, prio_prop, status_opt, prio_opt = pick_prop_ids(board)

    # Status/priority desired option IDs (from .env)
    status_want = None
    if args.status:
        status_want = {
            "todo": env("STATUS_TODO_ID"),
            "progress": env("STATUS_PROGRESS_ID"),
            "done": env("STATUS_DONE_ID"),
        }[args.status]

    prio_want = None
    if args.priority:
        prio_want = {
            "high": env("PRIORITY_HIGH_ID"),
            "medium": env("PRIORITY_MEDIUM_ID"),
            "low": env("PRIORITY_LOW_ID"),
        }[args.priority]

    # Get blocks
    st, blocks = http_json("GET", f"{base}/api/v2/boards/{board_id}/blocks", token)
    if st != 200 or not isinstance(blocks, list):
        die(f"Failed to get blocks ({st}): {blocks}")

    cards = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        if b.get("type") != "card":
            continue
        if int(b.get("deleteAt", 0) or 0) != 0:
            continue

        title = b.get("title", "")
        props = (b.get("fields") or {}).get("properties") or {}

        st_id = props.get(status_prop, "")
        pr_id = props.get(prio_prop, "")

        if status_want and st_id != status_want:
            continue
        if prio_want and pr_id != prio_want:
            continue
        if args.query and args.query.lower() not in title.lower():
            continue

        st_label = status_opt.get(st_id, st_id or "-")
        pr_label = prio_opt.get(pr_id, pr_id or "-")

        cards.append((b.get("id",""), st_label, pr_label, title))

    print(f"\nBoard: {board.get('title','')}  | cards: {len(cards)}\n")
    for row in cards[: max(args.limit, 1)]:
        cid, st_label, pr_label, title = row
        print(f"{cid}  |  {st_label:<12}  |  {pr_label:<10}  |  {title}")

if __name__ == "__main__":
    main()
