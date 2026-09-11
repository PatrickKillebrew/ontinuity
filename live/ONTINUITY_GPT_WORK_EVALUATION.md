# GPT B-Work Evaluation — Keep vs Discard
**Scope:** all 19 commits from pre-GPT `9a7eac2a` to B1 HEAD `0ef62d7` (68 files, ~14.9K insertions).
**Frame:** target is a SINGLE-USER Ontinuity. Keep genuine bug fixes / improvements; discard multi-seat
authorization machinery that defends against a threat single-user doesn't have.
**Method:** examined each commit's actual diff, not summaries.

---

## TIER 1 — STRONG KEEP (genuine improvements, single-user-relevant)

### B5-P Research Evidence Preservation  (commits `b69389a`, `3326753`, `5640170`)
The biggest real value in the whole B-work. Adds durable capture of what the adversarial engine actually did:
- **`app.py`**: model-call envelope capture (`_begin/_finish_model_call_envelope`), structured challenge
  recording (`record_structured_challenge`, `apply_upheld_challenge`), reproducibility manifests, session-
  start capture guards.
- **`db.py`**: real DB transactions (`begin/commit/rollback_transaction`), additive migrations,
  `insert_model_call_envelope`, `insert_reproducibility_manifest`, `insert_retraction_event`,
  `insert_session_execution`.
- **`workspace_db_endpoint.py`**: receipts table + `/api/query` route.
- Independently reviewed, 33/33 tests, 327 sessions preserved through it. Contract: `RESEARCH_PRESERVATION_CONTRACT.md`.
**Why keep:** this makes the adversarial output *auditable* — directly serves the "reliable output" pillar.
It's additive and provider-neutral; it does NOT depend on the B1 capability machinery.
**Tests to keep:** `test_research_preservation.py` (1062 lines).

### control_loop.py hardening  (part of B1 commits but independently valuable)
Changed from raw urlopen to validated response reading (`_read_response`, raises on non-JSON-object).
Adds input validation to `collect_pending_acks`, `triage`, mailbox/you_there response handling.
**Why keep:** these are defensive bug-fixes (fail loud on malformed responses) independent of authorization.

### db.py transaction safety
Real begin/commit/rollback transactions replacing bare commits. Prevents partial-write corruption.
**Why keep:** universal correctness improvement, single-user-relevant.

---

## TIER 2 — EVALUATE / CONDITIONAL KEEP

### verified_bootstrap_gate.md + gate mechanics changes
The current gate expects mechanics the pre-GPT 19-op engine doesn't implement (this is what makes a fresh
Control boot fail `oriented:false` right now). **If keeping the pre-GPT engine, the gate must be reconciled
back to what that engine implements.** So: keep the *engine* pre-GPT, roll the *gate* back to `9a7eac2a`'s
version (which passes against 19 ops). NOT a keep of GPT's gate — a keep of pre-GPT gate.

### release_baseline.py + B0 baseline tooling  (`release_baseline.py`, 496 lines)
The drift-audit tool that produced the B0 inventory. Genuinely useful for detecting repo-vs-box-vs-deploy
drift. **Conditional keep** — it's a good diagnostic, single-user-relevant, no B1 dependency. Worth keeping
as a standalone audit tool.

### egress/transport hardening (`ontinuity_https.sh`, prohibited-approaches lessons)
The curl `--disable --config -` discipline and "host-denial ≠ remote-result" rule. As DOCUMENTATION it's
valuable (codifies lessons that cost real time). As the B1 transport-lock CODE it's tangled with capability
machinery. **Keep the documentation/lessons; discard the capability-bound transport code.**

---

## TIER 3 — DISCARD (multi-seat authorization machinery; wrong for single-user)

- **`capability_auth.py`** + all capability admission — the whole "operator approves each capability" gate.
  Single-user operator authorizing themselves = pure friction. DISCARD.
- **`trusted_deploy.py`** (737 lines) + `trusted_deploy_protocol.md` — B1 two-party signed deploy behind
  box boundary. Single-user has no untrusted author to separate from deployer. DISCARD (the simple
  diag-key `deploy` op the pre-GPT engine has is sufficient).
- **B1 admission/transport envelope** (v2 request envelope, HTTP 428 gating, capability identity binding).
  DISCARD.
- **All capability test suites**: `test_capability_admission*.py`, `test_capability_box_identity.py`,
  `test_capability_courier.py`, `test_trusted_deploy.py`, `test_b1_*` — they test the discarded machinery. DISCARD.
- **B1 manifests** (`B1_INSTALL_MANIFEST.json`, `B1_TRANSPORT_LOCK_MANIFEST.json`) — describe the discarded
  build. DISCARD (keep in shelf/bundle for reference).
- **The `9a7eac2a`→ manual changes** that bumped 19→20 ops and added B1 mechanics language. DISCARD
  (roll manual back to pre-GPT).

---

## TIER 4 — RESTORE (things GPT DELETED that should come back)

- **`ipad_keyboard.py`** (545 lines) + CONTRACT + CORPUS — GPT DELETED this. It's a real, working tool
  (v15+ PASS: iPad soft keyboard → laptop char transmission) that solves the exact iPad-typing problem
  Patrick hit. **RESTORE from `9a7eac2a`.** Single-user-relevant (Patrick uses iPad).
- **`templates/kb.html`** (289 lines) — deleted alongside ipad_keyboard; part of the same tool. RESTORE.

---

## NET RECOMMENDATION

**A hybrid, not a pure rollback:**
1. **Engine:** already restored to pre-GPT `9a7eac2a` ✓ (done this session).
2. **Roll the box gate + manual back to `9a7eac2a`** so a fresh Control boot orients cleanly (fixes the
   `oriented:false` we found). Via `write_file`+`restart` (MAIN hands work now).
3. **Cherry-pick forward the Tier-1 keepers** onto the pre-GPT base: B5-P evidence preservation,
   control_loop hardening, db.py transactions. These are additive and don't need B1.
4. **Restore Tier-4 deletions** (ipad_keyboard).
5. **Discard all Tier-3** B1 authorization machinery (preserved in bundle `e15f5f46` if ever needed).
6. **Keep as standalone tools:** release_baseline.py (drift audit), the egress/curl documentation.

This gives a coherent, working, single-user-appropriate system that KEEPS the genuinely valuable evidence-
preservation and hardening work, RESTORES the useful deleted tools, and SHEDS the authorization machinery
that made the system cumbersome for one operator.

**Open decision for Patrick:** pure clean rollback to `9a7eac2a` (simplest, loses B5-P) vs. this hybrid
(keeps B5-P + hardening, more work to assemble). The hybrid is more effort but keeps real value.
