# SPEC — Per-identity keys done right (authenticated seat identity)

*Status: PROPOSE-ONLY (no build). Authored by worker1 (claude:opus-4.8) under KEYS-1. Grounds: live/specs/mailbox_threat_audit.md (SECAUDIT-1 box arm Q1-Q4 + SECAUDIT-2 engine arm), the actual code read via read_repo/read_file (_diag_ok, _ops_begin, mailbox_send/ack/fetch, _noself_predicate, diag_op_courier), the password-vault #42 pattern, and GATE2-1's issuance-on-pass stub. Inferences labeled.*

## THE CORE THEOREM (from the audit)
Per-identity keys are NECESSARY but NOT SUFFICIENT. The shared-key gate `_diag_ok()` (seat_mailbox.py ~L108, box_ops.py ~L39) proves only "a holder of THE key is calling" — never WHICH seat. Every seat identity in the system (from_seat, author_seat, claimed_by, ledger caller, the NOSELF filter input) is SELF-ASSERTED in the request body, not derived from authentication. Issuing distinct keys while routes still read identity from the body changes NOTHING — the key would prove "a valid node" without binding the asserted seat to it. The property that closes the holes is: **identity comes from WHICH key authenticated, and every route STOPS trusting body identity fields.** Keys are the enabler; the derive-and-ignore-body discipline is the fix.

## 1. KEY FORMAT + KEY -> SEAT MAPPING (no plaintext key stored)
- Each seat gets a distinct high-entropy key: `osk_<seat>_<random>` (osk = ontinuity seat key; the seat prefix is a HINT for humans, NOT the source of truth — identity is the lookup result, never the parsed prefix).
- Mapping is a KEYED LOOKUP with no plaintext key at rest, mirroring vault #42: store `sha256(key)` -> {seat, lineage, issued_at, status} in a key registry (a `seat_keys` table or the vault blob). On a request, hash the presented key and look it up; a hit yields the authenticated {seat, lineage}; a miss is 401. The plaintext key is never stored (only its hash), consistent with the no-credentials-on-box rule (a hash is repo/box-safe; the key itself lives only in the seat's sandbox + the operator's vault).
- Issuance: the operator's password-vault bootstrap (#42) KDF-decrypts the master key in-memory and seals/unseals per-seat keys; issuance writes a key-access grant row (the #42 sibling-of-operations_ledger). A seat's key is handed to it out-of-band (its boot packet), exactly as the shared DIAG_KEY is today — but now distinct per seat.
- Revocation: set status=revoked on the hash row; the next lookup fails closed. (Shared-key today has no revocation granularity — revoking it locks out everyone.)

## 2. THE GATE CHANGE (_diag_ok / the courier) — identity from auth, not body
- `_diag_ok()` becomes `_authenticate()` returning the DERIVED identity, not a bool:
  ```
  def _authenticate():
      presented = request.headers.get("X-Diag-Key","") or request.args.get("diag_key","")
      row = key_registry_lookup(sha256(presented))   # constant-time compare on the stored hash
      return row  # {seat, lineage, status} or None
  ```
  Every route starts with `ident = _authenticate(); if not ident or ident["status"]!="active": 401`. Routes then use `ident["seat"]` / `ident["lineage"]` as THE identity.
- BACK-COMPAT during migration: keep the shared DIAG_KEY accepted but mapped to a synthetic identity {seat:"unattributed", lineage:"shared-key"} so old callers still work but are visibly NOT a real seat (and can be denied on identity-sensitive routes). This lets keys roll out seat-by-seat without a flag day.
- THE COURIER (SECAUDIT-2 confirmed it is a PURE FORWARD: diag_op_courier ~L3379-3416 passes the body verbatim, no identity injection). Two options, INFERENCE-flagged tradeoff:
  (a) Keep the courier dumb and authenticate at the BOX: the seat presents its per-seat key as X-Diag-Key; the courier forwards it; the box's `_authenticate()` derives identity. Simplest — no engine change — but the engine then must forward the per-seat key (today it injects its OWN env DIAG_KEY to the box at ~L3410, so the box would see the ENGINE's key, not the seat's). So (a) requires the courier to PASS THROUGH the caller's key instead of substituting the env key. Small, surgical courier edit.
  (b) Authenticate at the ENGINE (courier derives identity, injects a signed `X-Seat-Identity` header the box trusts). More moving parts; introduces an engine->box trust header. NOT recommended first.
  RECOMMEND (a): courier passes the caller's key through; the box is the single authentication authority (it already owns the ledger + the contract). One trust boundary, box-side, matching where everything else is enforced.

## 3. THE MIGRATION — every route that reads identity from the body (cross-ref Q1-Q4)
For each, the body field becomes a REQUEST that is rejected/overridden on mismatch, never trusted as identity:
- **mailbox_send (Q1)** — currently reads from_seat/author_seat/from_lineage/author_lineage from the body (~L140, L156, L160-161) and inserts verbatim. CHANGE: from_seat := ident.seat (ignore/return-409 if body from_seat != ident.seat); from_lineage := ident.lineage; author_seat defaults to ident.seat but MAY be set to another seat ONLY when the sender is authorized to dispatch-on-behalf (control dispatching a worker's proposal) — a narrow, audited exception, not the default trust.
- **mailbox_fetch / you_there / _yt_try_claim (Q3)** — currently take seat/lineage from the body (~L178, L389) and write claimed_by from it (~L210, L363). CHANGE: claimed_by := ident.seat; lineage for the NOSELF check := ident.lineage. The body seat/roles become roles-to-accept only, never the claimer identity.
- **_noself_predicate (Q3 downstream)** — currently filters on COALESCE(author_seat,from_seat)=body-seat OR author_lineage=body-lineage (~L50). CHANGE: filter on ident.seat / ident.lineage (the DERIVED identity). This is what actually makes no-self-sign-off unbypassable — today a node relabels its seat string and the filter passes its own work through.
- **mailbox_ack (Q2)** — HARDEN-1 already added an optional claimed_by==seat guard, but seat is still body-supplied. CHANGE: drop the body seat; the guard becomes WHERE msg_id=? AND claimed_by=ident.seat unconditionally (no opt-out, no legacy no-seat path). This closes the HARDEN-1 "back-compat gap" I flagged: with derived identity there is no reason to allow an unguarded ack.
- **mailbox_reclaim (Q2)** — CHANGE: scope to ident.seat's own expired claims; the global all=true sweep restricted to a coordinator identity (a key whose registry row carries a coordinator role flag).
- **operations_ledger.caller (Q4)** — `_ops_begin(operation, tier, caller, source_ip, args)` currently gets caller="diag-key" hardcoded at every call site. CHANGE: pass caller=ident.seat (the DERIVED seat). This is CALLER-1's job (see §4); per-identity keys are what make that caller value TRUE instead of a guess. Keep source_ip but stop treating it as identity — SECAUDIT-2 showed it is always the relay's IP for courier ops anyway.

## 4. HOW IT COMPOSES WITH CALLER-1 + BOOTSTRAP-GATE ISSUANCE
- **CALLER-1 (caller stamping)** is the LEDGER half: write the seat into operations_ledger.caller instead of the constant "diag-key". Per-identity keys SUPPLY the trustworthy seat value CALLER-1 stamps. Order: CALLER-1 can land FIRST as a partial win (stamp the gate-derived or body-asserted seat, honestly labeled "asserted") — but it only becomes TRUSTWORTHY once keys derive the identity. So: CALLER-1 now (honest-but-asserted) -> keys later (caller becomes authenticated). They are the same column, two trust levels.
- **Bootstrap-gate issuance-on-pass (GATE2-1)** is the ISSUANCE trigger: /op/bootstrap_gate currently returns a key_issuance stub bound to {seat, lineage} with key_kind:"shared_diag_key_stub". When this spec builds, issuance-on-pass becomes REAL: a seat that PASSES the gate is issued (or has unsealed) its per-identity key, key_kind flips to "per_identity", and the registry row is written/activated. So the gate is the GATE on issuance (comply-or-fail at the credential layer): no pass, no key, no privileged hands. The stub's response shape was designed to not change when this lands.
- **Vault #42** is the CUSTODY layer: the master key that seals the per-seat keys is password-unlocked in-memory; issuance pulls from it. Keys depend on #42 for secure custody; the registry (hash->identity) is the runtime lookup #42 populates.

## 5. BUILD ORDER (proposed, operator-gated — NOT built here)
1. CALLER-1 — stamp seat into ledger caller (honest-asserted now). Cheap, immediate forensic win.
2. seat_keys registry (hash->{seat,lineage,status}) + `_authenticate()` returning derived identity, with shared-key back-compat -> "unattributed".
3. Migrate the routes (§3) one at a time to derived identity, each behind the back-compat shim, starting with the highest-severity (Q4 ledger already done by CALLER-1; then Q1 send, Q3 fetch/NOSELF, Q2 ack).
4. Courier pass-through of the caller's key (§2a) so the box sees the seat's key.
5. Bootstrap-gate issuance-on-pass becomes real (GATE2-1 stub -> per_identity); vault #42 custody.
6. Flip identity-sensitive routes to REJECT the shared-key "unattributed" identity; retire the shared key.

## ACCEPTANCE (how to prove it closes the audit)
- Q1: a node presenting worker2's key cannot send a message with from_seat="control" — the send overrides from_seat to "worker2" (or 409s). 
- Q3/NOSELF: a node cannot review its own proposal by relabeling — the NOSELF filter uses its key-derived seat, so its own work stays filtered regardless of body strings.
- Q2: a node cannot ack a block claimed by another seat — the ack WHERE-clause uses its key-derived seat unconditionally.
- Q4: operations_ledger.caller shows the real per-seat identity, not "diag-key"; a forged body seat does not appear anywhere as identity.

## PERSISTENCE-RULE TRAIL
Read the threat audit + the actual _diag_ok/_ops_begin/mailbox_*/\_noself_predicate/diag_op_courier code via read_repo + read_file (the box working copies and the live app.py). Grounded every migration target in a real line reference from the audit, confirmed against the code.
