#!/usr/bin/env bash
# Smoke tests for the Shopcarts Ingress.
# Sends requests through the Traefik Ingress and exits nonzero on any failure.
#
# Usage: k8s/test-ingress.sh [BASE_URL]
#   BASE_URL  defaults to http://127.0.0.1:8080
#   RETRIES   attempts per check (default 10), RETRY_DELAY seconds between them (default 3)

set -uo pipefail

BASE_URL="${1:-${BASE_URL:-http://127.0.0.1:8080}}"
BASE_URL="${BASE_URL%/}"
RETRIES="${RETRIES:-10}"
RETRY_DELAY="${RETRY_DELAY:-3}"

BODY_FILE="$(mktemp)"
trap 'rm -f "$BODY_FILE"' EXIT

failures=0

# fetch PATH -> sets HTTP_CODE, body in $BODY_FILE. Retries until 200 or attempts run out.
fetch() {
    local path="$1" attempt
    for ((attempt = 1; attempt <= RETRIES; attempt++)); do
        HTTP_CODE="$(curl -sS -o "$BODY_FILE" -w '%{http_code}' --max-time 5 "${BASE_URL}${path}" 2>/dev/null)" || HTTP_CODE="000"
        [[ "$HTTP_CODE" == "200" ]] && return 0
        if ((attempt < RETRIES)); then
            echo "  ... GET ${path} returned ${HTTP_CODE}, retrying (${attempt}/${RETRIES})"
            sleep "$RETRY_DELAY"
        fi
    done
    return 1
}

# check NAME PATH PYTHON_ASSERTION
# The assertion runs against the parsed JSON body bound to `data`.
check() {
    local name="$1" path="$2" assertion="$3"
    echo "Checking ${name}: GET ${BASE_URL}${path}"
    if ! fetch "$path"; then
        echo "  FAIL: expected HTTP 200, got ${HTTP_CODE}"
        [[ -s "$BODY_FILE" ]] && echo "  body: $(head -c 300 "$BODY_FILE")"
        failures=$((failures + 1))
        return
    fi
    if ! python3 -c "import json,sys; data=json.load(open(sys.argv[1])); sys.exit(0 if (${assertion}) else 1)" "$BODY_FILE" 2>/dev/null; then
        echo "  FAIL: HTTP 200 but unexpected body: $(head -c 300 "$BODY_FILE")"
        failures=$((failures + 1))
        return
    fi
    echo "  OK"
}

check "health endpoint" "/health" 'data == {"status": "OK"}'
check "shopcarts list"  "/api/shopcarts" 'isinstance(data, list)'

if ((failures > 0)); then
    echo "Ingress smoke tests FAILED (${failures} check(s))" >&2
    exit 1
fi
echo "Ingress smoke tests passed"
