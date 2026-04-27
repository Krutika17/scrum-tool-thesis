#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Load .env
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
else
  echo "ERROR: .env not found in $SCRIPT_DIR"
  exit 1
fi

: "${FOCALBOARD_URL:?Missing FOCALBOARD_URL in .env}"
: "${FOCALBOARD_TOKEN:?Missing FOCALBOARD_TOKEN in .env}"
: "${BOARD_ID:?Missing BOARD_ID in .env}"

: "${STATUS_PROP_ID:?Missing STATUS_PROP_ID in .env}"
: "${STATUS_TODO_ID:?Missing STATUS_TODO_ID in .env}"
: "${STATUS_PROGRESS_ID:?Missing STATUS_PROGRESS_ID in .env}"
: "${STATUS_DONE_ID:?Missing STATUS_DONE_ID in .env}"

: "${PRIORITY_PROP_ID:?Missing PRIORITY_PROP_ID in .env}"
: "${PRIORITY_HIGH_ID:?Missing PRIORITY_HIGH_ID in .env}"
: "${PRIORITY_MEDIUM_ID:?Missing PRIORITY_MEDIUM_ID in .env}"
: "${PRIORITY_LOW_ID:?Missing PRIORITY_LOW_ID in .env}"

CARD_ID="${1:-}"
shift || true

if [[ -z "$CARD_ID" ]]; then
  echo "Usage:"
  echo "  ./fb_update_v1.sh <CARD_ID> [--status todo|progress|done] [--priority high|medium|low] [--delete]"
  exit 2
fi

STATUS=""
PRIORITY=""
DO_DELETE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --status)   STATUS="${2:-}"; shift 2 ;;
    --priority) PRIORITY="${2:-}"; shift 2 ;;
    --delete)   DO_DELETE="true"; shift 1 ;;
    *) echo "ERROR: Unknown arg: $1"; exit 2 ;;
  esac
done


status_id=""
priority_id=""

case "$STATUS" in
  "") ;;
  todo)     status_id="$STATUS_TODO_ID" ;;
  progress) status_id="$STATUS_PROGRESS_ID" ;;
  done)     status_id="$STATUS_DONE_ID" ;;
  *) echo "ERROR: invalid --status (todo|progress|done)"; exit 2 ;;
esac

case "$PRIORITY" in
  "") ;;
  high)   priority_id="$PRIORITY_HIGH_ID" ;;
  medium) priority_id="$PRIORITY_MEDIUM_ID" ;;
  low)    priority_id="$PRIORITY_LOW_ID" ;;
  *) echo "ERROR: invalid --priority (high|medium|low)"; exit 2 ;;
esac

BASE="${FOCALBOARD_URL%/}"

API_BLOCKS_COLLECTION="$BASE/api/v2/boards/$BOARD_ID/blocks"
API_BLOCK_SINGLE="$BASE/api/v2/boards/$BOARD_ID/blocks/$CARD_ID"


BLOCKS_JSON="$(curl -sS "$API_BLOCKS_COLLECTION" \
  -H "Authorization: Bearer $FOCALBOARD_TOKEN" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Referer: $BASE/" \
  -H "Origin: $BASE"
)"


UPDATED_BLOCK_JSON="$(
  printf '%s' "$BLOCKS_JSON" | python3 -c '
import json,sys,time

blocks=json.load(sys.stdin)

card_id=sys.argv[1]
status_prop=sys.argv[2]
priority_prop=sys.argv[3]
status_id=sys.argv[4]
priority_id=sys.argv[5]
do_delete=(sys.argv[6] == "true")
board_id=sys.argv[7]

card=None
for b in blocks:
    if b.get("id")==card_id:
        card=b
        break
if not card:
    raise SystemExit(f"Card not found: {card_id}")

now=int(time.time()*1000)

card["boardId"]=board_id
card["updateAt"]=now
card.setdefault("fields", {})
card["fields"].setdefault("properties", {})
props=card["fields"]["properties"]

if status_id:
    props[status_prop]=status_id
if priority_id:
    props[priority_prop]=priority_id
if do_delete:
    card["deleteAt"]=now

print(json.dumps(card))
' "$CARD_ID" "$STATUS_PROP_ID" "$PRIORITY_PROP_ID" "$status_id" "$priority_id" "$DO_DELETE" "$BOARD_ID"
)"

# Helper: detect HTML responses
is_html() {
  echo "$1" | grep -qi "<!doctype html>"
}


RESP1="$(curl -sS -i --max-redirs 0 -X PUT "$API_BLOCK_SINGLE" \
  -H "Authorization: Bearer $FOCALBOARD_TOKEN" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Referer: $BASE/" \
  -H "Origin: $BASE" \
  --data "$UPDATED_BLOCK_JSON"
)"

if ! is_html "$RESP1"; then
  echo "$RESP1" | head -n 25
  exit 0
fi


PAYLOAD_ARRAY="[$UPDATED_BLOCK_JSON]"
RESP2="$(curl -sS -i --max-redirs 0 -X PUT "$API_BLOCKS_COLLECTION" \
  -H "Authorization: Bearer $FOCALBOARD_TOKEN" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Referer: $BASE/" \
  -H "Origin: $BASE" \
  --data "$PAYLOAD_ARRAY"
)"

echo "$RESP2" | head -n 25

if is_html "$RESP2"; then
  echo
  echo "ERROR: Update returned HTML (UI) instead of JSON."
  echo "That means this server build isn't accepting PUT updates via these endpoints."
  echo "Next step would be: use the exact endpoint the UI calls (we can grab it from DevTools)."
  exit 1
fi

