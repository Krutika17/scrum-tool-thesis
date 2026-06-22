#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

set -a
[ -f "$SCRIPT_DIR/.env" ] && source "$SCRIPT_DIR/.env"
set +a

: "${FOCALBOARD_URL:?Missing FOCALBOARD_URL in .env}"
: "${FOCALBOARD_USERNAME:?Missing FOCALBOARD_USERNAME in .env}"
: "${FOCALBOARD_PASSWORD:?Missing FOCALBOARD_PASSWORD in .env}"

BASE="${FOCALBOARD_URL%/}"

TOKEN="$(curl -sS -X POST "$BASE/api/v2/login" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  --data "{\"type\":\"normal\",\"username\":\"$FOCALBOARD_USERNAME\",\"password\":\"$FOCALBOARD_PASSWORD\"}" \
  | python3 -c 'import sys, json; print(json.load(sys.stdin).get("token", ""))')"

if [ -z "$TOKEN" ]; then
  echo "ERROR: login failed; no token returned" >&2
  exit 1
fi

python3 - "$SCRIPT_DIR/.env" "$TOKEN" <<'PY'
import re
import sys

env_path, token = sys.argv[1], sys.argv[2]
lines = open(env_path, encoding="utf-8").read().splitlines()

out, found = [], False
for line in lines:
    if re.match(r"\s*FOCALBOARD_TOKEN\s*=", line):
        out.append(f'FOCALBOARD_TOKEN="{token}"')
        found = True
    else:
        out.append(line)

if not found:
    out.insert(0, f'FOCALBOARD_TOKEN="{token}"')

open(env_path, "w", encoding="utf-8").write("\n".join(out) + "\n")
PY

echo "Token refreshed and written to .env"
