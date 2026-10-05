#!/bin/sh
# Bezpečnostné testy frontendu a nginx. Bežia nad skutočným Docker image.
#
#   sh frontend-new/tests/security.test.sh
#
# Overuje:
#   1. session_id ani claim token nie sú v žiadnej URL, ktorú appka skladá,
#   2. bezpečnostné hlavičky (CSP, X-Frame-Options, nosniff, Referrer-Policy)
#      sú na každej odpovedi (stránka, /assets/, /api/, chyby),
#   3. access log neobsahuje query string.
#
# Backend netreba: BACKEND_URL ukazuje na zatvorený port, /api/ teda vráti 502.
# Aj to je dobrý test, lebo hlavička musí prísť aj na chybovej odpovedi.

set -eu

cd "$(dirname "$0")/.."

IMAGE=naborova-frontend-security-test
CONTAINER=naborova-frontend-security-test
PORT=18089
SECRET=tajny-session-$$
FAILURES=0

fail() { echo "FAIL: $*"; FAILURES=$((FAILURES + 1)); }
pass() { echo "ok:   $*"; }

cleanup() { docker rm -f "$CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup EXIT

# --------------------------------------------------------------------------- #
# 1. Žiadne tajomstvo chatu v URL
# --------------------------------------------------------------------------- #

if grep -rnE '[?&](session|session_id|claim_token|claim)=' src; then
  fail "zdroják skladá URL so session/claim parametrom"
else
  pass "zdroják neskladá URL so session/claim parametrom"
fi

if grep -rn "searchParams.get('session" src; then
  fail "stránka číta session z URL"
else
  pass "žiadna stránka nečíta session z URL"
fi

# --------------------------------------------------------------------------- #
# 2. a 3. nginx nad skutočným image
# --------------------------------------------------------------------------- #

docker build -q -t "$IMAGE" . >/dev/null
cleanup
docker run -d --name "$CONTAINER" -p "$PORT:80" \
  -e BACKEND_URL=http://127.0.0.1:9 "$IMAGE" >/dev/null

for _ in 1 2 3 4 5 6 7 8 9 10; do
  curl -fs -o /dev/null "http://127.0.0.1:$PORT/" && break
  sleep 0.5
done

ASSET=$(docker exec "$CONTAINER" sh -c 'ls /usr/share/nginx/html/assets | head -n 1')

header() {
  # Hodnota hlavičky $2 v odpovedi na cestu $1 (case-insensitive názov).
  curl -s -o /dev/null -D - "http://127.0.0.1:$PORT$1" \
    | tr -d '\r' | awk -F': ' -v name="$2" 'tolower($1) == tolower(name) { print $2 }'
}

expect_header() {
  path=$1; name=$2; expected=$3
  value=$(header "$path" "$name")
  case "$value" in
    *"$expected"*) pass "$name na $path" ;;
    *) fail "$name na $path je '$value', čakám '$expected'" ;;
  esac
}

check_header() {
  expect_header "$1" Referrer-Policy "no-referrer"
  expect_header "$1" X-Frame-Options "DENY"
  expect_header "$1" X-Content-Type-Options "nosniff"
  expect_header "$1" Content-Security-Policy "frame-ancestors 'none'"
  expect_header "$1" Content-Security-Policy "script-src 'self';"
}

check_header "/"
check_header "/testovacia-firma/123/apply"
check_header "/assets/$ASSET"
expect_header "/assets/$ASSET" Cache-Control "immutable"
check_header "/assets/neexistuje.js"
check_header "/api/testovacia-firma/positions?session_id=$SECRET"

curl -s -o /dev/null "http://127.0.0.1:$PORT/testovacia-firma/123/apply?session=$SECRET"
sleep 0.5

# Len riadky access logu. error_log svoj formát nastaviť nevie a pri 502
# vypíše celý request, preto tajomstvo do URL nepatrí vôbec (bod 1).
# Riadok access logu má `] "GET …`, riadok error logu `request: "GET …`.
LOGS=$(docker logs "$CONTAINER" 2>&1 | grep -E '\] "[A-Z]+ ' || true)
if echo "$LOGS" | grep -q "$SECRET"; then
  fail "access log obsahuje query string:"
  echo "$LOGS" | grep "$SECRET"
else
  pass "access log neobsahuje query string"
fi
if echo "$LOGS" | grep -q '"GET /testovacia-firma/123/apply HTTP'; then
  pass "access log stále loguje cestu"
else
  fail "access log neloguje cestu requestu"
fi

echo
if [ "$FAILURES" -gt 0 ]; then
  echo "$FAILURES test(ov) zlyhalo"
  exit 1
fi
echo "všetko prešlo"
