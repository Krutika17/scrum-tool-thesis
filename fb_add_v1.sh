#!/usr/bin/env bash
set -euo pipefail

# --- load .env from same folder as this script ---
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# auto-export vars loaded from .env so Python can see them
set -a
[ -f "$SCRIPT_DIR/.env" ] && source "$SCRIPT_DIR/.env"
set +a


: "${FOCALBOARD_TOKEN:?Missing FOCALBOARD_TOKEN in .env}"
: "${BOARD_ID:?Missing BOARD_ID in .env}"
: "${PARENT_ID:?Missing PARENT_ID in .env}"

: "${STATUS_PROP_ID:?Missing STATUS_PROP_ID in .env}"
: "${STATUS_TODO_ID:?Missing STATUS_TODO_ID in .env}"
: "${STATUS_PROGRESS_ID:?Missing STATUS_PROGRESS_ID in .env}"
: "${STATUS_DONE_ID:?Missing STATUS_DONE_ID in .env}"

: "${PRIORITY_PROP_ID:?Missing PRIORITY_PROP_ID in .env}"
: "${PRIORITY_HIGH_ID:?Missing PRIORITY_HIGH_ID in .env}"
: "${PRIORITY_MEDIUM_ID:?Missing PRIORITY_MEDIUM_ID in .env}"
: "${PRIORITY_LOW_ID:?Missing PRIORITY_LOW_ID in .env}"

BASE_URL="${FOCALBOARD_URL:-http://localhost:8000}"

TITLE="${1:-}"
STATUS="${2:-todo}"        # todo|progress|done
PRIORITY="${3:-medium}"    # high|medium|low

if [[ -z "$TITLE" ]]; then
  echo "Usage: ./fb_add.sh \"Task title\" {todo|progress|done} {high|medium|low}"
  exit 2
fi

case "$STATUS" in
  todo)     STATUS_ID="$STATUS_TODO_ID" ;;
  progress) STATUS_ID="$STATUS_PROGRESS_ID" ;;
  done)     STATUS_ID="$STATUS_DONE_ID" ;;
  *)
    echo "Invalid status: $STATUS (use todo|progress|done)"
    exit 2
    ;;
esac

case "$PRIORITY" in
  high)   PRIORITY_ID="$PRIORITY_HIGH_ID" ;;
  medium) PRIORITY_ID="$PRIORITY_MEDIUM_ID" ;;
  low)    PRIORITY_ID="$PRIORITY_LOW_ID" ;;
  *)
    echo "Invalid priority: $PRIORITY (use high|medium|low)"
    exit 2
    ;;
esac

NOW_MS="$(python3 - <<'PY'
import time
print(int(time.time()*1000))
PY
)"

# API expects an ARRAY of blocks
PAYLOAD="$(python3 - <<PY
import json
now=int("$NOW_MS")

data=[{
  "id": "",
  "parentId": "$PARENT_ID",
  "schema": 1,
  "type": "card",
  "title": "$TITLE",
  "fields": {
    "icon": "📝",
    "isTemplate": False,
    "properties": {
      "$STATUS_PROP_ID": "$STATUS_ID",
      "$PRIORITY_PROP_ID": "$PRIORITY_ID"
    }
  },
  "createAt": now,
  "updateAt": now,
  "deleteAt": 0,
  "boardId": "$BOARD_ID"
}]
print(json.dumps(data))
PY
)"

curl -sS -i -X POST "$BASE_URL/api/v2/boards/$BOARD_ID/blocks" \
  -H "Authorization: Bearer $FOCALBOARD_TOKEN" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Referer: $BASE_URL/" \
  --data "$PAYLOAD" | head -n 25

echo


