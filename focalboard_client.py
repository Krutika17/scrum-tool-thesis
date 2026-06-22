import json
import secrets
import string
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"

_env = {}


def _load_env_file(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        _env.setdefault(k, v)


_load_env_file(ENV_PATH)


def _need(name: str) -> str:
    v = _env.get(name, "").strip()
    if not v:
        print(f"Missing env var: '{name}'", file=sys.stderr)
        sys.exit(2)
    return v


def get_config(name: str, default: str = "") -> str:
    return _env.get(name, default)


BASE = _need("FOCALBOARD_URL").rstrip("/")
TOKEN = _need("FOCALBOARD_TOKEN")
BOARD_ID = _need("BOARD_ID")
PARENT_ID = _need("PARENT_ID")

STATUS_PROP_ID = _need("STATUS_PROP_ID")
STATUS_TODO_ID = _need("STATUS_TODO_ID")
STATUS_PROGRESS_ID = _need("STATUS_PROGRESS_ID")
STATUS_DONE_ID = _need("STATUS_DONE_ID")

PRIORITY_PROP_ID = _need("PRIORITY_PROP_ID")
PRIORITY_HIGH_ID = _need("PRIORITY_HIGH_ID")
PRIORITY_MEDIUM_ID = _need("PRIORITY_MEDIUM_ID")
PRIORITY_LOW_ID = _need("PRIORITY_LOW_ID")

STATUS_MAP = {"todo": STATUS_TODO_ID, "progress": STATUS_PROGRESS_ID, "done": STATUS_DONE_ID}
PRIORITY_MAP = {"high": PRIORITY_HIGH_ID, "medium": PRIORITY_MEDIUM_ID, "low": PRIORITY_LOW_ID}

BLOCKS_URL = f"{BASE}/api/v2/boards/{BOARD_ID}/blocks"
BOARD_URL = f"{BASE}/api/v2/boards/{BOARD_ID}"


def _request(method: str, url: str, payload=None):
    data = None
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE}/",
        "Origin": BASE,
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, resp.headers.get("Content-Type", ""), body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, e.headers.get("Content-Type", ""), body


def _now_ms() -> int:
    return int(time.time() * 1000)


def _gen_id(n: int = 26) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def _get_board():
    st, ctype, body = _request("GET", BOARD_URL)
    if st != 200 or "application/json" not in (ctype or ""):
        raise RuntimeError(f"Failed to get board ({st}): {body[:400]}")
    return json.loads(body)


def _get_blocks():
    st, ctype, body = _request("GET", BLOCKS_URL)
    if st != 200 or "application/json" not in (ctype or ""):
        raise RuntimeError(f"Failed to get blocks ({st}): {body[:400]}")
    return json.loads(body)


def _get_block(block_id: str):
    for b in _get_blocks():
        if isinstance(b, dict) and b.get("id") == block_id:
            return b
    return None


def _prop_option_labels(board):
    status_opt = {}
    prio_opt = {}
    for p in (board.get("cardProperties") or []):
        if p.get("type") != "select":
            continue
        pid = p.get("id")
        if pid == STATUS_PROP_ID:
            for o in p.get("options", []):
                status_opt[o["id"]] = o.get("value", o["id"])
        if pid == PRIORITY_PROP_ID:
            for o in p.get("options", []):
                prio_opt[o["id"]] = o.get("value", o["id"])
    return status_opt, prio_opt


def list_work_items(status=None, priority=None, query=None, limit=10):
    board = _get_board()
    status_opt, prio_opt = _prop_option_labels(board)

    status_want = STATUS_MAP.get(status) if status else None
    prio_want = PRIORITY_MAP.get(priority) if priority else None

    items = []
    for b in _get_blocks():
        if not isinstance(b, dict) or b.get("type") != "card":
            continue
        if int(b.get("deleteAt", 0) or 0) != 0:
            continue

        title = b.get("title", "")
        props = (b.get("fields") or {}).get("properties") or {}
        st_id = props.get(STATUS_PROP_ID, "")
        pr_id = props.get(PRIORITY_PROP_ID, "")

        if status_want and st_id != status_want:
            continue
        if prio_want and pr_id != prio_want:
            continue
        if query and query.lower() not in title.lower():
            continue

        items.append({
            "id": b.get("id", ""),
            "title": title,
            "status": status_opt.get(st_id, st_id or "-"),
            "priority": prio_opt.get(pr_id, pr_id or "-"),
        })

    return {
        "board_title": board.get("title", ""),
        "items": items[: max(limit, 1)],
        "total": len(items),
    }


def update_status(card_id: str, status=None, priority=None, delete=False):
    block_url = f"{BLOCKS_URL}/{card_id}"

    current = _get_block(card_id)
    if not current:
        raise ValueError(f"Block not found on this board: {card_id}")

    if delete:
        st, ctype, body = _request("DELETE", block_url, {})
        if st not in (200, 204):
            raise RuntimeError(f"DELETE failed: HTTP {st} {body[:800]}")
        after = _get_block(card_id)
        if after is not None:
            raise RuntimeError(f"DELETE returned success, but block still exists: {card_id}")
        return {"id": card_id, "deleted": True}

    props = ((current.get("fields") or {}).get("properties") or {}).copy()

    if status:
        s = status.lower()
        if s not in STATUS_MAP:
            raise ValueError("Invalid status. Use todo|progress|done")
        props[STATUS_PROP_ID] = STATUS_MAP[s]

    if priority:
        p = priority.lower()
        if p not in PRIORITY_MAP:
            raise ValueError("Invalid priority. Use high|medium|low")
        props[PRIORITY_PROP_ID] = PRIORITY_MAP[p]

    patch_body = {
        "deletedFields": [],
        "updatedFields": {
            "properties": props,
            "contentOrder": (current.get("fields") or {}).get("contentOrder", []) or [],
        },
    }

    st, ctype, body = _request("PATCH", block_url, patch_body)
    if st not in (200, 204):
        raise RuntimeError(f"PATCH failed: HTTP {st} {body[:800]}")

    verify = _get_block(card_id)
    if not verify:
        raise RuntimeError("Block disappeared after PATCH (unexpected).")

    vprops = ((verify.get("fields") or {}).get("properties") or {})
    want_status = STATUS_MAP.get(status.lower()) if status else None
    want_prio = PRIORITY_MAP.get(priority.lower()) if priority else None

    if want_status and vprops.get(STATUS_PROP_ID) != want_status:
        raise RuntimeError("PATCH returned success, but status did NOT change.")
    if want_prio and vprops.get(PRIORITY_PROP_ID) != want_prio:
        raise RuntimeError("PATCH returned success, but priority did NOT change.")

    return {"block": verify, "raw_response_text": body}


def add_note(card_id: str, note_text: str):
    card = None
    for b in _get_blocks():
        if b.get("id") == card_id and b.get("type") == "card":
            card = b
            break
    if not card:
        raise ValueError(f"Card not found on this board: {card_id}")

    existing_order = (card.get("fields") or {}).get("contentOrder", []) or []
    if not isinstance(existing_order, list):
        existing_order = []

    ts = _now_ms()
    created_by = card.get("createdBy", "")

    note_block = {
        "id": _gen_id(),
        "parentId": card_id,
        "createdBy": created_by,
        "modifiedBy": created_by,
        "schema": 1,
        "type": "text",
        "title": note_text,
        "fields": {},
        "createAt": ts,
        "updateAt": ts,
        "deleteAt": 0,
        "boardId": BOARD_ID,
    }

    st, ctype, body = _request("POST", BLOCKS_URL, [note_block])
    if st not in (200, 201):
        raise RuntimeError(f"POST note failed: HTTP {st} {body[:800]}")

    created = json.loads(body) if body.strip() else []
    note_id = created[0].get("id") if isinstance(created, list) and created else note_block["id"]

    patch_body = {
        "deletedFields": [],
        "updatedFields": {
            "contentOrder": list(existing_order) + [note_id],
        },
    }
    pst, pctype, pbody = _request("PATCH", f"{BLOCKS_URL}/{card_id}", patch_body)
    if pst not in (200, 204):
        raise RuntimeError(f"PATCH contentOrder failed: HTTP {pst} {pbody[:800]}")

    return created


def create_card(title: str, status: str = "todo", priority: str = "medium"):
    s = status.lower()
    p = priority.lower()
    if s not in STATUS_MAP:
        raise ValueError("Invalid status. Use todo|progress|done")
    if p not in PRIORITY_MAP:
        raise ValueError("Invalid priority. Use high|medium|low")

    ts = _now_ms()
    payload = [{
        "id": "",
        "parentId": PARENT_ID,
        "schema": 1,
        "type": "card",
        "title": title,
        "fields": {
            "icon": "📝",
            "isTemplate": False,
            "properties": {
                STATUS_PROP_ID: STATUS_MAP[s],
                PRIORITY_PROP_ID: PRIORITY_MAP[p],
            },
        },
        "createAt": ts,
        "updateAt": ts,
        "deleteAt": 0,
        "boardId": BOARD_ID,
    }]

    st, ctype, body = _request("POST", BLOCKS_URL, payload)
    if st not in (200, 201):
        raise RuntimeError(f"Card creation failed: HTTP {st} {body[:800]}")

    result = json.loads(body) if body.strip() else []
    created = result[0] if isinstance(result, list) and result else result
    return created


def create_standup(yesterday: str, today: str, blockers: str, title: str = None):
    from datetime import datetime

    standup_title = title or f"Standup — {datetime.now().strftime('%Y-%m-%d')}"
    card = create_card(standup_title, "todo", "medium")
    standup_id = card.get("id", "")

    add_note(standup_id, f"Yesterday: {yesterday}")
    add_note(standup_id, f"Today: {today}")
    add_note(standup_id, f"Blockers: {blockers}")

    return {"standup_card_id": standup_id, "title": standup_title}


def create_impediment(description: str):
    title = f"IMPEDIMENT: {description}"
    card = create_card(title, "todo", "high")
    return {"card_id": card.get("id", ""), "title": title}


def resolve_impediment(card_id: str, note: str):
    update_status(card_id, status="done", priority="low")
    add_note(card_id, note)
    return {"card_id": card_id, "resolved": True}


def _read_log_events():
    log_path = SCRIPT_DIR / "logs" / "actions.jsonl"
    if not log_path.exists():
        return []
    events = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except Exception:
            pass
    events.sort(key=lambda e: e.get("ts_ms", 0))
    return events


def _standup_fields(e):
    extra = e.get("extra", {})
    extra = extra if isinstance(extra, dict) else {}
    return {
        "yesterday": extra.get("yesterday", e.get("yesterday", "")),
        "today": extra.get("today", e.get("today", "")),
        "blockers": extra.get("blockers", e.get("blockers", "")),
    }


def _impediment_state(events):
    impediments = {}
    for e in events:
        action = e.get("action", "")
        card_id = e.get("card_id", "")
        title = e.get("title", "")
        status = e.get("status", "")

        if not card_id:
            continue

        if action == "imp":
            impediments[card_id] = {
                "card_id": card_id,
                "title": title,
                "created_ts_ms": e.get("ts_ms", 0),
                "last_ts_ms": e.get("ts_ms", 0),
                "status": "OPEN",
            }
            continue

        if card_id not in impediments:
            continue

        impediments[card_id]["last_ts_ms"] = e.get("ts_ms", impediments[card_id]["last_ts_ms"])

        if action in ("resolve", "done"):
            impediments[card_id]["status"] = "RESOLVED"
        elif action in ("move", "update") and status == "done":
            impediments[card_id]["status"] = "RESOLVED"
        elif action == "delete":
            impediments[card_id]["status"] = "RESOLVED"

    return list(impediments.values())


def build_report():
    events = _read_log_events()
    standups = [e for e in events if e.get("action") == "standup"]
    impediments = _impediment_state(events)

    return {
        "events": events,
        "standups": [
            {
                "ts_ms": e.get("ts_ms", 0),
                "card_id": e.get("card_id", ""),
                "title": e.get("title", ""),
                **_standup_fields(e),
            }
            for e in standups
        ],
        "impediments": impediments,
        "open_impediments": [i for i in impediments if i.get("status") == "OPEN"],
        "resolved_impediments": [i for i in impediments if i.get("status") == "RESOLVED"],
    }
