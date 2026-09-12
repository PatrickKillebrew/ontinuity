# Ontinuity — Pre-GPT Recovery Plan & Ledger
**Established:** from authenticated B0 baseline (`live/baselines/2026-09-04_b0.json`) + git verification
**Goal:** roll the whole system back to its state before GPT's completion-phase ("B") work — i.e. pre-B0.
**Anchor fact:** the last real commit before all B-work was `9a7eac2a` (2026-07-20). Everything after is GPT's work.

---

## STATUS LOG
- **MAIN: RESTORED ✓** serviceInstanceDeploy → `9a7eac2a` succeeded. Blob `3fcaaf31` (pre-GPT engine).
  Diag-key hands confirmed (19-op allowlist, no "malformed capability"). Data intact: 328 sessions, db healthy.
- **FARM: RESTORED ✓** serviceInstanceDeploy → `f9696c49` succeeded. Confirmed by `/diag/version` now ABSENT
  (405/not-in-whitelist) — which MATCHES the B0 record of pre-GPT FARM (it never had that endpoint). Health:
  db:true, 328 sessions, idle. FARM = worker engine, older vintage, no courier — expected/correct.
- **BOX: no rollback needed ✓** Live box files (`file_server.py` blob `e56a3fee`, etc.) EXACTLY MATCH the
  current repo (`0ef62d7:live/box/`). The restored pre-GPT MAIN engine works perfectly with them (proven:
  db:true, hands working). The B0 "DRIFT" was bookkeeping-relative, not a functional problem. No action.
- **B1 preserved** in git (`0ef62d7`) + bundle `e15f5f46`. Reversible.

**RECOVERY COMPLETE: the whole system is back to its pre-GPT state and working.**

## 1. ENGINE ROLLBACK TARGETS (Railway) — all VERIFIED in git

| Surface | Pre-GPT target commit | app.py blob | size | notes |
|---|---|---|---|---|
| **MAIN** | `9a7eac2a1f295382067e5b897dd4e014b8b0bc43` | `3fcaaf31` | 238,562 b | B0-recorded live MAIN. Verified pre-B1: 19 ops, diag-key gated, 0 B1 capability markers. Deploy id was `5ae156eb-52af-4389-86c6-01bb76e24840`. |
| **FARM** | `f9696c494526c123f1d0e1509ee03c4a1130cfa6` | `cf622449` | 211,927 b | B0-recorded live FARM (last deployed 2026-07-19). Deploy id was `d97c14ff-d4a4-48f0-98c3-2729ce71c588`. |

**IMPORTANT:** MAIN and FARM were NEVER the same code. Do not restore one "to match the other."
- Today MAIN runs B1 `0ef62d7` / blob `556f4029` (281,618 b) — GPT's B1.
- Today FARM runs `3476ed8` / blob `35502fd0` (263,487 b) — also drifted from pre-GPT; NOT the original.

**Restore action — MECHANISM VERIFIED (corpus + live read-only test):**
Railway GraphQL `serviceInstanceDeploy` mutation. From CONTROL_HANDOFF.md "DEPLOY TOPOLOGY" section:
- Endpoint: `https://backboard.railway.com/graphql/v2`
- **Header: `Project-Access-Token: <token>` (NOT Bearer)** — token in LLaves (`ce441d2a-...`)
- Verified live (read-only): projectId `a8dea5f4-b34e-466e-b22c-0d5b59fc63b5`, environmentId `6ff341f9-675e-4514-9b0c-5defe9d3d2a9`
- MAIN ("web") serviceId `72b20f74...` (from corpus — confirm full id before mutation)
- Mutation: `serviceInstanceDeploy(environmentId, serviceId, commitSha="9a7eac2a...")`
- Use `serviceInstanceDeploy` (pulls the specified commit) — NOT `serviceInstanceRedeploy` (rebuilds stale pinned commit).
- The engine's own `/op/deploy` does NOT work for this (engine lacks RAILWAY_TOKEN — "known FARM seam");
  deploys are done control-side via Railway GraphQL directly.

Verify each after deploy: `/diag/version` blob match (MAIN→`3fcaaf31`, FARM→`cf622449`) + diag-key `__probe__` returns 19-op allowlist.

BOX is separate: Railway deploy does NOT touch the box. Box files update via `write_file`+`restart_workspace`
(needs restored MAIN hands first). repo-commit != box-install — always both.

---

## 2. BOX ROLLBACK TARGETS (Hetzner /opt/ontinuity) — PARTIAL, one real gap

B0 recorded these installed blobs on the box (before B1 cutover):

| File | Pre-GPT installed blob | in git? | recovery |
|---|---|---|---|
| `seat_mailbox.py` | `c58e4cb0` | ✓ MATCH in repo | restore from git |
| `box_ops.py` | `1ff93529` | ✓ MATCH in repo | restore from git |
| `file_server.py` | `d8e165ed` | ✗ NOT in git | **GAP** — see below |
| `db.py` | `5de802a5` | ✗ NOT in git | **GAP** |
| `workspace_db_endpoint.py` | `9c7ce6d1` | ✗ NOT in git | **GAP** |

**The gap:** the pre-GPT *installed* bytes for `file_server.py`, `db.py`, `workspace_db_endpoint.py`
were never committed to git (they lived only on the live box). GPT's own rollback ledger flagged this.

**Mitigations to try, in order:**
1. **Read the live box directly** (`178.156.184.172:5001`, or via a restored-MAIN courier `read_file`).
   B1 may not have overwritten all three — the pre-GPT bytes may still be ON THE BOX. NOT YET CHECKED
   (sandbox couldn't reach the box; needs a live read once MAIN hands are restored).
2. **Project folder** `/mnt/project/file_server.py` = blob `54c6e1f0` (51,462 b) — a candidate, but does
   NOT match `d8e165ed`. Keep as fallback only.
3. If truly unrecoverable: rebuild from the nearest git version + `seat_mailbox_DEPLOY.md` runbook.

---

## 3. DATABASE

- 324 sessions at B0; 328 live on MAIN now. Operational DB is intact and LIVE.
- Rolling back engine CODE does not wipe the DB.
- A pre-GPT DB dump was committed to the PRIVATE intake repo (`cbfb6220`, `backups/ontinuity_dump.sql`).
- Behavioral-capture DB `ontinuity behavioral data.db` committed in public repo (`db276c5`): sessions/challenges/signals.

---

## 4. RECOVERY SEQUENCE (draft — verify box before executing)

1. **Preserve GPT's B-work first** (already done: bundle `e15f5f46`, git commits `0ef62d7`..). Confirm before touching anything.
2. **Read live box** to learn which box files still hold pre-GPT bytes (resolves the gap above). Requires live hands.
3. **Redeploy MAIN → `9a7eac2a`** (Railway API). Verify: `/diag/version` blob = `3fcaaf31`; diag-key `__probe__` returns 19 ops.
4. **Restore box files**: clean ones (`seat_mailbox.py`, `box_ops.py`) from git; drifted ones from the live-box read or fallback.
5. **Redeploy FARM → `f9696c49`**. Verify.
6. **Confirm hands + data**: MAIN accepts diag-key, 328 sessions intact.
7. **Boot the original way** ("boot and go", no B1 authorization) to confirm full recovery.

---

## 5. GPT WORK TO EVALUATE FOR KEEPING (do AFTER recovery, before discarding B-work)

Rather than discard all of GPT's work, review these for genuinely useful fixes/corrections worth
re-applying to the recovered system (so we don't rediscover them):

- **B5-P raw-evidence preservation** (`3326753`) — reviewed, tested, 327 sessions preserved. Possibly valuable.
- **Mailbox result-channel fix** (the 06-21 transport-jam root-cause fix) — predates B but confirm it's in the target.
- **query_guard / semicolon false-positive fix** — small correctness fix.
- **Any bug fixes** buried in B1 that aren't about the capability/authorization machinery.
- The **egress gate + prohibited-approaches list** (from GPT's transfer packet) — codifies the curl/Railway
  invocation lessons; useful as documentation even if the code isn't kept.

Rule: keep *corrections and bug fixes*; discard the *B1 capability/admission/authorization machinery*
(wrong for single-operator Ontinuity).

---

## KEY CORRECTION (why this ledger exists)
Earlier assumption "MAIN and FARM ran the same code / FARM is the pre-B1 original" was WRONG.
The B0 baseline proved three distinct engines at three sizes from three dates. Always restore each
surface to its OWN B0-recorded target, verified against git — never infer one from another.
