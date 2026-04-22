#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.env"

: "${FOCALBOARD_URL:?Missing FOCALBOARD_URL in .env}"
: "${FOCALBOARD_USERNAME:?Missing FOCALBOARD_USERNAME in .env}"
: "${FOCALBOARD_PASSWORD:?Missing FOCALBOARD_PASSWORD in .env}"

COOKIE_JAR="$SCRIPT_DIR/cookies.txt"
LOGIN_URL="$FOCALBOARD_URL/api/v2/login"

# Fresh cookie jar
rm -f "$COOKIE_JAR"

echo "Logging in to: $LOGIN_URL"

curl -sS -c "$COOKIE_JAR" -X POST "$LOGIN_URL" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  --data "{\"username\":\"$FOCALBOARD_USERNAME\",\"password\":\"$FOCALBOARD_PASSWORD\"}" \
  >/dev/null

echo "Saved cookies to: $COOKIE_JAR"
echo "Cookie lines: $(wc -l < "$COOKIE_JAR")"

# Check CSRF cookie exists
CSRF_TOKEN="$(awk '$6=="MMCSRF"{print $7}' "$COOKIE_JAR" | tail -n 1)"
if [ -z "$CSRF_TOKEN" ]; then
  CSRF_TOKEN="$(awk '$6=="csrf"{print $7}' "$COOKIE_JAR" | tail -n 1)"
fi

if [ -z "$CSRF_TOKEN" ]; then
  echo "ERROR: Could not fetch MMCSRF/csrf cookie. Login likely failed (wrong password/username) or server config differs."
  echo "Tip: run: curl -i -X POST \"$LOGIN_URL\" ... and check response."
  exit 1
fi

echo "OK: CSRF cookie fetched."
