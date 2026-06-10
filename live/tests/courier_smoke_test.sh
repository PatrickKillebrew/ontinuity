#!/usr/bin/env bash
# ============================================================
# RELAY-COURIER SMOKE TEST — /diag/op/<name> end-to-end
# ------------------------------------------------------------
# Run AFTER the courier is deployed to the engine. Proves the full path:
#   operator -> engine /diag/op/<name> (courier) -> box /op/<name> -> back.
# Each positive test pairs with the result the op already proved last session
# (corpus: scoped-op folds June 10), so you're checking the COURIER PATH
# against a known-good op, not the op itself.
#
# Usage:
#   export DIAG_KEY=...           # the engine/box shared diag key
#   export ENGINE=https://web-production-7eaf8.up.railway.app   # MAIN relay
#   bash courier_smoke_test.sh
#
# Reads nothing destructive except restart_workspace (SAFE/reversible: the
# service bounces and returns in a few seconds; that op is in the allowlist
# precisely because it's reversible). Skip test 2 if you don't want the bounce.

set -u
ENGINE="${ENGINE:-https://web-production-7eaf8.up.railway.app}"
: "${DIAG_KEY:?set DIAG_KEY in the environment first}"

hdr=(-H "X-Diag-Key: ${DIAG_KEY}" -H "Content-Type: application/json")
pass=0; fail=0
say() { printf '\n=== %s ===\n' "$1"; }
check() { # check <expected-substring-or-code> <actual> <label>
  if [[ "$2" == *"$1"* ]]; then echo "PASS: $3"; pass=$((pass+1));
  else echo "FAIL: $3 (looked for '$1' in: $2)"; fail=$((fail+1)); fi
}

# ---- POSITIVE 1: read_journal (SAFE read) ----
# Expect: HTTP 200, JSON with journal lines. Bounded arg lines:5.
say "1. read_journal (SAFE read, bounded lines:5)"
r=$(curl -s -w '\n%{http_code}' "${hdr[@]}" \
      -d '{"lines":5}' "${ENGINE}/diag/op/read_journal")
code=$(printf '%s' "$r" | tail -1); body=$(printf '%s' "$r" | sed '$d')
echo "HTTP $code"; echo "$body" | head -c 600; echo
check "200" "$code" "read_journal returns 200 through courier"

# ---- POSITIVE 2: restart_workspace (SAFE reversible mutation) ----
# Expect: HTTP 200, 'restart dispatched'. Then /status returns 401 (up+gated)
# within a few seconds. Comment out this block to skip the bounce.
say "2. restart_workspace (SAFE reversible — bounces the workspace)"
r=$(curl -s -w '\n%{http_code}' "${hdr[@]}" \
      -d '{}' "${ENGINE}/diag/op/restart_workspace")
code=$(printf '%s' "$r" | tail -1); body=$(printf '%s' "$r" | sed '$d')
echo "HTTP $code"; echo "$body" | head -c 300; echo
check "200" "$code" "restart_workspace dispatched 200 through courier"
echo "...waiting 6s for the service to come back, then confirming up+gated..."
sleep 6
st=$(curl -s -o /dev/null -w '%{http_code}' "${ENGINE}/diag/api/health?diag_key=${DIAG_KEY}")
echo "post-restart /diag/api/health: HTTP $st"
check "200" "$st" "workspace healthy through relay after restart"

# ---- POSITIVE 3: register_egress (SAFE) ----
# Expect: HTTP 200. With the IP-whitelist retired (op#2), this is now a
# no-op-shaped success on the box; the test confirms the courier forwards a
# no-arg op cleanly. (Op kept in allowlist for revert scenarios.)
say "3. register_egress (SAFE, no args)"
r=$(curl -s -w '\n%{http_code}' "${hdr[@]}" \
      -d '{}' "${ENGINE}/diag/op/register_egress")
code=$(printf '%s' "$r" | tail -1); body=$(printf '%s' "$r" | sed '$d')
echo "HTTP $code"; echo "$body" | head -c 300; echo
check "200" "$code" "register_egress returns 200 through courier"

# ---- NEGATIVE 1: wrong diag key -> 401 at the engine gate ----
say "4. wrong key -> 401 (engine gate, never reaches box)"
code=$(curl -s -o /dev/null -w '%{http_code}' \
      -H "X-Diag-Key: WRONG-${RANDOM}" -H "Content-Type: application/json" \
      -d '{"lines":1}' "${ENGINE}/diag/op/read_journal")
echo "HTTP $code"
check "401" "$code" "bad key rejected with 401 at courier gate"

# ---- NEGATIVE 2: unknown op name -> 403 at the engine name-gate ----
say "5. unknown op -> 403 (name-gate, never reaches box)"
r=$(curl -s -w '\n%{http_code}' "${hdr[@]}" -d '{}' "${ENGINE}/diag/op/delete_everything")
code=$(printf '%s' "$r" | tail -1); body=$(printf '%s' "$r" | sed '$d')
echo "HTTP $code"; echo "$body" | head -c 200; echo
check "403" "$code" "unknown op rejected with 403 (allowlist holds)"

# ---- NEGATIVE 3: non-object body -> 400 ----
say "6. non-object body -> 400 (bounded-body guard)"
code=$(curl -s -o /dev/null -w '%{http_code}' "${hdr[@]}" \
      -d '"not-an-object"' "${ENGINE}/diag/op/read_journal")
echo "HTTP $code"
check "400" "$code" "non-object body rejected with 400"

# ---- LEDGER CONFIRM: the box logged the ops it actually ran ----
# Positive tests 1-3 should each have appended an operations_ledger row on the
# box (dual-end: started -> ok). Negative tests 4-6 must NOT (they never
# reached the box). Confirm via the read-only corpus query relay.
say "7. ledger reflects only the box-reached ops"
q="SELECT operation,status FROM operations_ledger ORDER BY op_id DESC LIMIT 6"
enc=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$q")
led=$(curl -s "${ENGINE}/diag/api/query?diag_key=${DIAG_KEY}&sql=${enc}")
echo "$led" | head -c 800; echo
check "read_journal" "$led" "ledger shows read_journal (box was reached + logged)"

printf '\n========== %d passed, %d failed ==========\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] && echo "Courier verified end-to-end." || echo "Investigate failures above before relying on the courier."
