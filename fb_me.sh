#!/usr/bin/env bash
set -euo pipefail
source .env

curl -s "http://localhost:8000/api/v2/users/me" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer ${FOCALBOARD_TOKEN}" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Referer: http://localhost:8000/"
