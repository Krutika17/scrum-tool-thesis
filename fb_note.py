#!/usr/bin/env python3
import os, sys, json, time, secrets, string, urllib.request, urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"

def load_env_file(path: Path):
    """Load .env even if variables aren't exported."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)

load_env_file(ENV_PATH)

def need(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        print(f"Missing env var: '{name}'", file=sys.stderr)
        sys.exit(2)
    return v

BASE = need("FOCALBOARD_URL").rstrip("/")
TOKEN = need("FOCALBOARD_TOKEN")
BOARD_ID = need("BOARD_ID")

def now_ms() -> int:
    return int(time.time() * 1000)

def gen_id(n: int = 26) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))

def request_json(method: str, url: str, payload=None):
    data = None
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE}/",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            ctype = resp.headers.get("Content-Type", "")
            if "application/json" not in ctype:
                print(f"HTTP {resp.status}  Content-Type: {ctype}", file=sys.stderr)
                print(body[:400], file=sys.stderr)
                raise RuntimeError("Server returned non-JSON response (likely UI HTML).")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTPError {e.code} on {url}", file=sys.stderr)
        print(body[:400], file=sys.stderr)
        raise

def usage():
    print(
        "Usage:\n"
        "  ./fb_note.py <CARD_ID> \"Note text\"\n\n"
        "Example:\n"
        "  ./fb_note.py cxcm... \"Blocked: waiting for access\"\n"
    )

def main():
    if len(sys.argv) < 3:
        usage()
        sys.exit(2)

    card_id = sys.argv[1]
    note_text = sys.argv[2]

    blocks_url = f"{BASE}/api/v2/boards/{BOARD_ID}/blocks"
    blocks = request_json("GET", blocks_url)

    # Find the card block
    card = None
    for b in blocks:
        if b.get("id") == card_id and b.get("type") == "card":
            card = b
            break
    if not card:
        print("ERROR: Card not found on this board:", card_id, file=sys.stderr)
        sys.exit(2)

    # Ensure contentOrder exists
    card.setdefault("fields", {})
    card["fields"].setdefault("contentOrder", [])
    if not isinstance(card["fields"]["contentOrder"], list):
        card["fields"]["contentOrder"] = []

    # Create a new text block under the card
    nid = gen_id()
    ts = now_ms()

    created_by = card.get("createdBy", "")
    note_block = {
        "id": nid,
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

    # Append note block id to the card content order
    card["fields"]["contentOrder"].append(nid)
    card["updateAt"] = ts
    if "modifiedBy" in card and created_by:
        card["modifiedBy"] = created_by

    # Upsert both: new note block + updated card
    result = request_json("POST", blocks_url, [note_block, card])
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
