# GPT Week — Complete Deep Dive: What's Actually Valuable
Full read of every non-B1 change from pre-GPT `9a7eac2a` to `0ef62d7`. Answers "the week found and
fixed a lot of holes — what's worth keeping?"

---

## FIRST, THE HONEST REFRAME
A lot of what *looked* like GPT's hole-finding is **already yours.** These fix-specs all predate GPT
(they exist at `9a7eac2a` — you + prior-Claude found and fixed them before the GPT week):
`cyclenum_fix`, `query_guard_fix`, `deploy_drift_check`, `farmfix_verify`, `erl_decision`,
`signoff_gate_v2_spec`. **They're already in your restored foundation.** GPT didn't add them.

So the real question narrows to: what did GPT *specifically* add? Here's the complete list, assessed.

---

## WHAT B5-P ACTUALLY ADDS (the value, precisely)
Not "behavioral scoring" — it's narrower and more foundational than that. From the contract:

**B5-P preserves the raw, immutable evidence of what the adversarial engine did, so it can never be
silently lost or falsified.** Specifically it captures, per session:
- exact model-call envelopes (prompts, responses, host-only — never secrets)
- structured challenge events (claim, grounds, ruling) + append-only retractions (a correction links
  to its cause, never erases it)
- a reproducibility manifest (non-secret role config, code revision) so any later analysis is replayable
- honest-unknown discipline (missing history stays NULL; configured ≠ authenticated identity)

**Why it's valuable for YOUR goal:** your second pillar is "reliable output." Reliability you can't *audit*
is just a claim. B5-P is what lets you (or your BIL, or a skeptic) walk back from any adversarial output
to exactly what was challenged, upheld, retracted, and why — with the raw bytes preserved and secrets
excluded by construction. It's the evidence spine under "the output is trustworthy."
**It is additive and does NOT depend on B1's capability machinery.** Clean keep.

**Caveat:** parts of B5-P's identity handling reference "PENDING_B1_B2" — since we're discarding B1, those
degrade gracefully to "UNVERIFIED" (which is honest and fine for single-user). No blocker.

---

## THE COMPLETE LIST OF GPT-ADDED THINGS

### KEEP — genuine value, single-user-relevant
1. **B5-P evidence preservation** (`RESEARCH_PRESERVATION_CONTRACT.md` + app.py capture + db.py inserts +
   workspace_db_endpoint receipts/`/api/query`). The auditability spine. *Best thing in the week.*
2. **`release_baseline.py`** — a read-only drift-audit tool: composes GitHub + Railway + engine + courier +
   box + box-file-hash observations into one report, exits 0=clean/1=drift/2=unknown. Genuinely useful for
   a single operator to answer "is what's deployed what's in my repo?" No B1 dependency. **Keep as a tool.**
   (It's literally what would have told us MAIN drifted, in one command.)
3. **`control_loop.py` hardening** — response validation: raises on non-JSON-object mailbox_peek/you_there
   responses instead of silently proceeding. Small, defensive, correct. **Keep.**
4. **`db.py` transaction safety** — real begin/commit/rollback vs bare commits; prevents partial-write
   corruption. Universal correctness. **Keep.**
5. **The B0 baseline** (`2026-09-04_b0.json`) — the authenticated snapshot that made this whole recovery
   possible (it's how we found the true pre-GPT MAIN commit). **Keep as historical evidence.**

### KEEP AS DOCUMENTATION (not code)
6. **The `2026-09-03` cross-vendor succession record** — proves the engine is genuinely model/platform-
   agnostic: a ChatGPT conversation inherited the Control office through the existing corpus + 19-op
   courier, with NO engine rewrite. This is *important validation* of the core architecture and directly
   relevant to the BIL goal (any operator, any model, seats through config + boot). **Keep the record.**
7. **The egress/curl discipline** (from the transfer packet's prohibited-approaches list) — codifies the
   `curl --disable --config -` lesson and "host-denial ≠ remote-result." Valuable as documentation; the
   corpus already half-had it. **Fold the lessons in.**

### RESTORE — GPT deleted these; they're useful
8. **`ipad_keyboard.py`** + CONTRACT + CORPUS + **`templates/kb.html`** — a real, working (v15+ tested)
   tool for iPad→laptop typing. Solves a problem Patrick actually has. GPT deleted it. **Restore from `9a7eac2a`.**

### DISCARD — B1 authorization machinery (wrong for single-user; preserved in bundle)
- `capability_auth.py`, `trusted_deploy.py`, B1 transport envelope, the v2 HTTPS protocol, all capability/
  admission/trusted-deploy test suites, both B1 manifests, `restart_burnin` op, the 20-op manual language.
- Also the release-board / completion-plan docs (`ONTINUITY_1_0_BOARD.md`, `COMPLETION_PLAN.md`) — these
  are the B-block plan itself; keep in shelf as history, not active.

---

## NET: what the week was actually worth
Strip away B1 (the 60-70% that was churn on machinery you don't need), and the genuine residue is:
- **B5-P** — real, valuable, keep (auditability spine)
- **release_baseline.py** — real, valuable, keep (drift tool)
- **db.py transactions + control_loop hardening** — real, small, keep
- **the cross-vendor proof + B0 baseline** — valuable evidence, keep as record
- **ipad_keyboard** — restore (GPT wrongly deleted)

That's a meaningful ~30% of real value — matching GPT's own honest self-estimate. Not nothing. But most
of it is *additive* and can be cherry-picked onto the clean pre-GPT foundation without dragging B1 along.

## RECOMMENDED HYBRID STEP ORDER (remaining after Step 1 done)
- **Step 2:** cherry-pick B5-P (engine capture + db.py inserts + workspace endpoint) onto pre-GPT engine, redeploy MAIN, verify capture on a test session.
- **Step 3:** add `release_baseline.py` as a standalone tool (no engine change).
- **Step 4:** restore `ipad_keyboard` from `9a7eac2a`.
- **Step 5:** keep control_loop + db.py hardening (comes with B5-P cherry-pick, since they're in the same files).
- Leave B1 shelved in the bundle. Fold the cross-vendor record + egress lessons into the corpus as docs.
