#!/usr/bin/env python3
import os, sys, json, time, urllib.request, urllib.error
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
    v = os.environ.get(name, "").strip()
    if not v:
        print(f"Missing env var: '{name}'", file=sys.stderr)
        sys.exit(2)
    return v

BASE = need("FOCALBOARD_URL").rstrip("/")
TOKEN = need("FOCALBOARD_TOKEN")
BOARD_ID = need("BOARD_ID")

STATUS_PROP_ID = need("STATUS_PROP_ID")
STATUS_TODO_ID = need("STATUS_TODO_ID")
STATUS_PROGRESS_ID = need("STATUS_PROGRESS_ID")
STATUS_DONE_ID = need("STATUS_DONE_ID")

PRIORITY_PROP_ID = need("PRIORITY_PROP_ID")
PRIORITY_HIGH_ID = need("PRIORITY_HIGH_ID")
PRIORITY_MEDIUM_ID = need("PRIORITY_MEDIUM_ID")
PRIORITY_LOW_ID = need("PRIORITY_LOW_ID")

STATUS_MAP = {"todo": STATUS_TODO_ID, "progress": STATUS_PROGRESS_ID, "done": STATUS_DONE_ID}
PRIORITY_MAP = {"high": PRIORITY_HIGH_ID, "medium": PRIORITY_MEDIUM_ID, "low": PRIORITY_LOW_ID}

def request(method: str, url: str, payload=None, content_type="application/json"):
    data = None
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "Content-Type": content_type,
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
            ctype = resp.headers.get("Content-Type", "")
            return resp.status, ctype, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, e.headers.get("Content-Type", ""), body

def get_block(blocks_url: str, block_id: str):
    st, ctype, body = request("GET", blocks_url, None, "application/json")
    if st != 200 or "application/json" not in (ctype or ""):
        print(f"GET blocks failed: HTTP {st} {ctype}", file=sys.stderr)
        print((body or "")[:500], file=sys.stderr)
        return None
    blocks = json.loads(body) if body else []
    for b in blocks:
        if isinstance(b, dict) and b.get("id") == block_id:
            return b
    return None

def usage():
    print(
        "Usage:\n"
        "  ./fb_update.py <CARD_ID> [--status todo|progress|done] [--priority high|medium|low] [--delete]\n"
    )

def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(2)

    block_id = sys.argv[1]
    status = None
    priority = None
    do_delete = False

    i = 2
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--status":
            status = sys.argv[i + 1]; i += 2
        elif a == "--priority":
            priority = sys.argv[i + 1]; i += 2
        elif a == "--delete":
            do_delete = True; i += 1
        else:
            print("Unknown arg:", a, file=sys.stderr)
            usage()
            sys.exit(2)

    blocks_url = f"{BASE}/api/v2/boards/{BOARD_ID}/blocks"
    block_url  = f"{BASE}/api/v2/boards/{BOARD_ID}/blocks/{block_id}"

    # Ensure block exists first
    current = get_block(blocks_url, block_id)
    if not current:
        print("ERROR: Block not found on this board:", block_id, file=sys.stderr)
        sys.exit(2)

    # DELETE mode (UI uses DELETE with {} body)
    if do_delete:
        st, ctype, body = request("DELETE", block_url, {}, "application/json")
        if st not in (200, 204):
            print(f"DELETE failed: HTTP {st} {ctype}", file=sys.stderr)
            print((body or "")[:800], file=sys.stderr)
            sys.exit(1)

        # Verify it is actually gone
        after = get_block(blocks_url, block_id)
        if after is not None:
            print("ERROR: DELETE returned success, but block still exists.", file=sys.stderr)
            print("VERIFY: id=", block_id, "deleteAt=", after.get("deleteAt", 0), "type=", after.get("type", "?"), file=sys.stderr)
            sys.exit(1)

        print("{}")
        return

    # PATCH mode (match UI payload shape)
    props = ((current.get("fields") or {}).get("properties") or {}).copy()

    if status:
        s = status.lower()
        if s not in STATUS_MAP:
            print("Invalid --status. Use todo|progress|done", file=sys.stderr)
            sys.exit(2)
        props[STATUS_PROP_ID] = STATUS_MAP[s]

    if priority:
        p = priority.lower()
        if p not in PRIORITY_MAP:
            print("Invalid --priority. Use high|medium|low", file=sys.stderr)
            sys.exit(2)
        props[PRIORITY_PROP_ID] = PRIORITY_MAP[p]

    patch_body = {
        "deletedFields": [],
        "updatedFields": {
            "properties": props,
            # UI often includes contentOrder; safe to include empty list if missing
            "contentOrder": (current.get("fields") or {}).get("contentOrder", []) or []
        }
    }

    st, ctype, body = request("PATCH", block_url, patch_body, "application/json")
    if st not in (200, 204):
        print(f"PATCH failed: HTTP {st} {ctype}", file=sys.stderr)
        print((body or "")[:800], file=sys.stderr)
        sys.exit(1)

    # Verify change
    verify = get_block(blocks_url, block_id)
    if not verify:
        print("ERROR: Block disappeared after PATCH (unexpected).", file=sys.stderr)
        sys.exit(1)

    vprops = ((verify.get("fields") or {}).get("properties") or {})
    want_status = STATUS_MAP.get(status.lower()) if status else None
    want_prio = PRIORITY_MAP.get(priority.lower()) if priority else None

    if want_status and vprops.get(STATUS_PROP_ID) != want_status:
        print("ERROR: PATCH returned success, but status did NOT change.", file=sys.stderr)
        print("VERIFY status=", vprops.get(STATUS_PROP_ID), "wanted=", want_status, file=sys.stderr)
        sys.exit(1)

    if want_prio and vprops.get(PRIORITY_PROP_ID) != want_prio:
        print("ERROR: PATCH returned success, but priority did NOT change.", file=sys.stderr)
        print("VERIFY priority=", vprops.get(PRIORITY_PROP_ID), "wanted=", want_prio, file=sys.stderr)
        sys.exit(1)

    # Some servers return {} for PATCH; keep it simple
    if body.strip():
        print(body)
    else:
        print("{}")

if __name__ == "__main__":
    main()

