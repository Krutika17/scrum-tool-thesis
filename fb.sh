#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  ./fb add  "Title" [--status todo|progress|done] [--priority high|medium|low]
  ./fb todo "Title"
  ./fb prog "Title"

  ./fb list [--limit N] [--query TEXT]
  ./fb search "TEXT"

  ./fb move <CARD_ID> [--status todo|progress|done] [--priority high|medium|low]
  ./fb done <CARD_ID>
  ./fb high <CARD_ID>
  ./fb low  <CARD_ID>
  ./fb delete <CARD_ID>

  ./fb note <CARD_ID> "Note text"

  ./fb imp "Impediment text"
  ./fb impediments
  ./fb resolve <CARD_ID> "Resolved: ..."

  ./fb standup

  ./fb report activity --last 10
  ./fb report standup --last 7
  ./fb report impediments
  ./fb report impediments --open
  ./fb report today

  ./fb export --type activity
  ./fb export --type standup
  ./fb export --type impediments
USAGE
}

if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
else
  echo "ERROR: .env not found in $SCRIPT_DIR"
  exit 1
fi

extract_id() {
  python3 -c '
import sys, json, re

s = sys.stdin.read()

m = re.search(r"(\{.*|\[.*)", s, re.DOTALL)
body = m.group(1).strip() if m else s.strip()

card_id = ""

try:
    data = json.loads(body)
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        card_id = data[0].get("id", "")
    elif isinstance(data, dict):
        card_id = data.get("id", "")
except Exception:
    m2 = re.search(r"\"id\"\s*:\s*\"([^\"]+)\"", body)
    if m2:
        card_id = m2.group(1)

print(card_id)
'
}

cmd="${1:-}"
[[ -z "$cmd" ]] && { usage; exit 2; }
shift || true

case "$cmd" in
  add)
    TITLE="${1:-}"
    [[ -z "$TITLE" ]] && { echo "ERROR: Missing title"; usage; exit 2; }
    shift || true

    STATUS="todo"
    PRIORITY="medium"

    while [[ $# -gt 0 ]]; do
      case "$1" in
        --status)   STATUS="${2:-}"; shift 2 ;;
        --priority) PRIORITY="${2:-}"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *) echo "ERROR: Unknown arg: $1"; usage; exit 2 ;;
      esac
    done

    OUT="$("$SCRIPT_DIR/fb_add_v1.sh" "$TITLE" "$STATUS" "$PRIORITY")"
    echo "$OUT"
    CID="$(printf '%s' "$OUT" | extract_id)"
    python3 "$SCRIPT_DIR/fb_log.py" add --card "$CID" --title "$TITLE" --status "$STATUS" --priority "$PRIORITY" || true
    ;;

  todo)
    TITLE="${1:-}"
    [[ -z "$TITLE" ]] && { echo "ERROR: Missing title"; usage; exit 2; }
    OUT="$("$SCRIPT_DIR/fb_add_v1.sh" "$TITLE" "todo" "medium")"
    echo "$OUT"
    CID="$(printf '%s' "$OUT" | extract_id)"
    python3 "$SCRIPT_DIR/fb_log.py" todo --card "$CID" --title "$TITLE" --status "todo" --priority "medium" || true
    ;;

  prog)
    TITLE="${1:-}"
    [[ -z "$TITLE" ]] && { echo "ERROR: Missing title"; usage; exit 2; }
    OUT="$("$SCRIPT_DIR/fb_add_v1.sh" "$TITLE" "progress" "medium")"
    echo "$OUT"
    CID="$(printf '%s' "$OUT" | extract_id)"
    python3 "$SCRIPT_DIR/fb_log.py" prog --card "$CID" --title "$TITLE" --status "progress" --priority "medium" || true
    ;;

  list)
    exec "$SCRIPT_DIR/fb_list.py" "$@"
    ;;

  search)
    q="${1:-}"
    [[ -z "$q" ]] && { echo "ERROR: Missing search text"; usage; exit 2; }
    exec "$SCRIPT_DIR/fb_list.py" --query "$q"
    ;;

  move)
    cid="${1:-}"
    [[ -z "$cid" ]] && { echo "ERROR: Missing CARD_ID"; usage; exit 2; }
    shift || true

    STATUS=""
    PRIORITY=""

    while [[ $# -gt 0 ]]; do
      case "$1" in
        --status)   STATUS="${2:-}"; shift 2 ;;
        --priority) PRIORITY="${2:-}"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *) echo "ERROR: Unknown arg: $1"; usage; exit 2 ;;
      esac
    done

    args=("$cid")
    [[ -n "$STATUS" ]] && args+=("--status" "$STATUS")
    [[ -n "$PRIORITY" ]] && args+=("--priority" "$PRIORITY")

    "$SCRIPT_DIR/fb_update.py" "${args[@]}"
    python3 "$SCRIPT_DIR/fb_log.py" move --card "$cid" --status "$STATUS" --priority "$PRIORITY" || true
    ;;

  done)
    cid="${1:-}"
    [[ -z "$cid" ]] && { echo "ERROR: Missing CARD_ID"; usage; exit 2; }
    "$SCRIPT_DIR/fb_update.py" "$cid" --status done
    python3 "$SCRIPT_DIR/fb_log.py" done --card "$cid" --status done || true
    ;;

  high)
    cid="${1:-}"
    [[ -z "$cid" ]] && { echo "ERROR: Missing CARD_ID"; usage; exit 2; }
    "$SCRIPT_DIR/fb_update.py" "$cid" --priority high
    python3 "$SCRIPT_DIR/fb_log.py" high --card "$cid" --priority high || true
    ;;

  low)
    cid="${1:-}"
    [[ -z "$cid" ]] && { echo "ERROR: Missing CARD_ID"; usage; exit 2; }
    "$SCRIPT_DIR/fb_update.py" "$cid" --priority low
    python3 "$SCRIPT_DIR/fb_log.py" low --card "$cid" --priority low || true
    ;;

  delete)
    cid="${1:-}"
    [[ -z "$cid" ]] && { echo "ERROR: Missing CARD_ID"; usage; exit 2; }
    "$SCRIPT_DIR/fb_update.py" "$cid" --delete
    python3 "$SCRIPT_DIR/fb_log.py" delete --card "$cid" || true
    ;;

  note)
    cid="${1:-}"
    shift || true
    note_text="${*:-}"
    [[ -z "$cid" || -z "$note_text" ]] && { echo "ERROR: note needs <CARD_ID> and text"; usage; exit 2; }
    "$SCRIPT_DIR/fb_note.py" "$cid" "$note_text"
    python3 "$SCRIPT_DIR/fb_log.py" note --card "$cid" --extra "$note_text" || true
    ;;

  imp)
    text="${1:-}"
    [[ -z "$text" ]] && { echo "ERROR: Missing impediment text"; usage; exit 2; }
    TITLE="IMPEDIMENT: $text"
    OUT="$("$SCRIPT_DIR/fb_add_v1.sh" "$TITLE" "todo" "high")"
    echo "$OUT"
    CID="$(printf '%s' "$OUT" | extract_id)"
    python3 "$SCRIPT_DIR/fb_log.py" imp --card "$CID" --title "$TITLE" --status todo --priority high || true
    ;;

  impediments)
    exec "$SCRIPT_DIR/fb_impediments.py"
    ;;

  resolve)
    cid="${1:-}"
    shift || true
    msg="${*:-}"
    [[ -z "$cid" || -z "$msg" ]] && { echo "ERROR: resolve needs <CARD_ID> and message"; usage; exit 2; }

    "$SCRIPT_DIR/fb_update.py" "$cid" --status done --priority low
    "$SCRIPT_DIR/fb_note.py" "$cid" "$msg"
    python3 "$SCRIPT_DIR/fb_log.py" resolve --card "$cid" --extra "$msg" --status done --priority low || true
    echo '{"ok": true}'
    ;;

  standup)
    exec "$SCRIPT_DIR/fb_standup.py"
    ;;

  report)
    exec "$SCRIPT_DIR/fb_report.py" "$@"
    ;;

  export)
    exec "$SCRIPT_DIR/fb_report.py" export "$@"
    ;;

  -h|--help|help)
    usage
    ;;

  *)
    echo "ERROR: Unknown command: $cmd"
    usage
    exit 2
    ;;
esac