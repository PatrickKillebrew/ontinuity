# POST-B1 ALIGNMENT RECOVERY REGISTER

**Recorded:** 2026-09-09
**Source inspected:** exact independently accepted B1 commit
`0ef62d7dfce76891cebae7b2484ca592dd663246`
**Status:** source-grounded recovery inventory; not an execution queue, release
authorization, deploy object, or claim that a dormant path is production-ready
**Authority:** `live/ONTINUITY_1_0_BOARD.md` still selects work. This register is
consulted after B1, and B3 remains the next dependency lane.

## 1. Why this register exists

The B1 correction exposed a recurring failure mode: Ontinuity already contained
useful machinery, but a Control seat could overlook it and begin designing a new
path. This pass searched the current corpus and source before any further build.
Its purpose is to make the existing parts retrievable when their release block
arrives, without allowing the inventory itself to pre-empt the board.

The governing rule is:

> Resolve and reuse the existing mechanism first. Add architecture only when a
> release acceptance test proves that the existing mechanism cannot satisfy it.

## 2. B1 boundary and resumption point

- The immutable B1 deploy object is
  `0ef62d7dfce76891cebae7b2484ca592dd663246`, tree
  `ae5b68302c1b24e7efc085e53f007e57ea3dc3ae`.
- A clean independent reviewer accepted its exact bytes after reproducing 216 of
  216 tests, both manifest hashes, coverage, and byte-preserving verification.
- Install-manifest SHA-256:
  `18690b97a1a1ae7f50e1ff6ac682c8210f7d5d60807e50786a25e454a7413214`.
- Transport-manifest SHA-256:
  `6279166a9f25c21405f5f51bfc048345547b16ab7e8603ff852f4eadc1324c0b`.
- At capture time, public `main` and the installed six-file box unit remained at
  `b596d3c`; MAIN remained `693435a`, FARM remained rollback `3476ed8`, and the
  matching burn-in source had not been restarted.
- No finding below changes the B1 object or authorizes publication, box install,
  restart, credential use, or deployment. B1 resumes with a fresh proposal and
  distinct-seat signoff bound to `0ef62d7...`, followed by Patrick's explicit
  authorization for that same SHA. The cutover then follows the accepted trusted
  boundary in manifest order. B3 follows B1.

This document lives on a separate post-B1 documentation branch so its prose
cannot be mistaken for part of the accepted deploy object.

## 3. Established Results Ledger: three layers, not one

| Layer | Current source | Disposition | Existing use | Reconciliation point |
|---|---|---|---|---|
| Session-local established-result memory | `active_session["session_ledger"]` and `active_session["results_board"]` in `app.py` | **ACTIVE / PROVEN IN SOURCE** | Results are accumulated, injected into later turns and judges, reconciled after adjudication, and carried into close/distillation. | Preserve through B3. Use as an input when B5 checks the complete evidence chain. |
| Project/branch file ERL | `get_erl_filename`, `session_erl_path`, `github_push_erl`, `write_erl_ledger`, and `run_projenius_synthesize` in `app.py`; `erl_main_main.txt` | **ACTIVE MECHANISM / PARTIALLY PROVEN** | Projenius receives the current complete ledger during SYNTHESIZE; the returned complete ledger is written wholesale with a truncation guard and a GitHub push attempt. Deployed in `28ba127`; one real ledger file was written in `8aefd5e`. | Inspect under B5/B7 before relying on it for orientation. Do not rebuild it from the old proposal memo. |
| Structured ERL | `established_results`, `projenius_ledger_operations`, and writer/read methods in `db.py` | **DORMANT WRITE PATH** | Schema and readers exist. `insert_established_result`, `confirm_result`, and `retract_result` have no production caller in current `app.py`. | Activate only if B5's evidence-chain acceptance or B7's boot test demonstrates that the file/fold record is insufficient. Avoid a second source of truth by default. |

### ERL seams to test, not assume

1. `prompts/projenius_system.txt` says ORIENT receives the current ERL, branch
   registry, Knowtext Active Frameworks/Open Questions, and objective.
   `run_projenius_orient()` currently sends only the objective and the whole
   Knowtext working-context extraction. The file ERL is read during SYNTHESIZE,
   not during ORIENT. The already-present box routes `/api/ledger` and
   `/api/project_state` describe themselves as Projenius feeds, but current
   `app.py` does not consume them.
2. `write_erl_ledger()` writes the local file, calls `github_push_erl()`, ignores
   its Boolean result, and returns the number of `RESULT:` entries. The close
   sequence can therefore announce that the ledger was updated after the local
   write even when remote persistence failed. The GitHub helper emits its own
   error, but the final success wording is not durable-persistence proof.
3. No focused current test module covers ERL parsing, project/branch isolation,
   truncation, remote-push failure semantics, or ORIENT inputs.
4. `live/specs/erl_decision.md` predates the file-backed implementation. Its
   statement that `app.py` has no ERL persistence path is superseded for the
   file layer, but remains true for the structured SQLite writer.

These are bounded inspection findings, not a reason to reopen B1. Before making
an ERL change, define which ledger is authoritative, which is an index, and what
failure must block a close or boot.

## 4. Existing Hetzner/box machinery

### 4.1 Trusted mechanical courier surface

The current engine allowlist already names twenty bounded box operations:

`read_journal`, `restart_workspace`, `restart_burnin`, `register_egress`,
`mailbox_send`, `mailbox_fetch`, `mailbox_ack`, `mailbox_peek`,
`mailbox_reclaim`, `mailbox_purge`, `write_file`, `commit_self`, `read_file`,
`commit_file`, `you_there`, `read_repo`, `bootstrap_gate`, `deploy`,
`seed_tenant`, and `backup_db`.

That does **not** mean a model receives all twenty. B1 deliberately keeps the
initial model grant to `bootstrap_gate`, `read_repo`, `mailbox_send`,
`mailbox_fetch`, `mailbox_ack`, `mailbox_peek`, and `you_there`, plus the probe.
Deploy is separately operator-confirmed, exact-object-bound, and short-lived.
The remaining operations are operator/root surfaces unless a later reviewed
policy explicitly says otherwise.

This is the only machinery to extend for trusted box administration. A future
seat must not invent SSH, a free-form shell, a different HTTP client, or a new
Railway GraphQL path when a named operation already exists.

### 4.2 Legacy workspace substrate worth recovering under B6

`live/box/file_server.py` already contains:

- persistent `config.json` and `workspace_state.json`;
- project listing, creation, and switching;
- decisions, sessions, and AI context;
- authenticated file read/write, change history, rollback, audit, and manifest;
- repository search and database/project-state endpoints;
- Governor routes, settings, status, and scoped operations.

Useful B6 substrate is the project/config/state/history/rollback/audit/search
model. It should be reconciled and hardened rather than replaced.

Two concrete defects must be fixed before treating the legacy workspace surface
as a reproducible trusted layer:

- `safe_path()` uses string-prefix containment, so a sibling whose name shares
  the project-directory prefix can pass. Reuse the canonical/common-path rule
  already proved in the B1 protected-file correction.
- `/write` passes `changed` to `audit()` before assigning it, after the target
  file has already been written. That can produce a post-mutation 500 and an
  ambiguous client-visible outcome.

The exact-string `/run` route uses `shell=True`, and `/settings` can change its
allowlist. These are legacy operator workspace surfaces. They are **not** the
trusted-deploy path and must not be promoted into a model capability. The B1
manual expressly preserves the named-operation boundary.

## 5. Governor, database, intake, and dormant seams

### Governor

- Current `app.py` already exposes `/governor`, `/governor/data`, and
  `/governor/workers`.
- Current Governor HTML has more than one source location. At this snapshot,
  `templates/governor.html` and `live/governor/governor.html` are byte-identical;
  `live/box/governor.html` differs.
- Preserved branch `codex/governor-observability` at `5e3310d` adds activity and
  punch-list observability plus tests. It diverges from current B1 history.
  Treat it as source material and selectively port/review the needed delta under
  B6; never merge the old branch wholesale.

### Database and intake

- The active receive-session path persists sessions, transcript, artifacts,
  Knowtext, challenges, model calls, reproducibility data, retractions,
  behavioral observations, and executions.
- Public DB methods with no current production caller include the structured ERL
  writers, `insert_intake_session`, and several transcript/challenge/
  high-friction helper methods. Existence is not evidence of an active feature.
- The `intake_sessions` table is not the current intake store. `/intake_chat`,
  `/intake_capture`, and `/intake_resume` persist bounded JSON to the private
  intake repository. Existing low-priority watch items—rate/cost, intake-only
  prompt injection, junk accumulation, transient `Thinking...`, and final-capture
  UX—remain watch items unless reproduced or required by a release test.
- Box `/api/ledger` can read structured established results and
  `/api/project_state` can assemble an orientation view, but the engine does not
  currently use those feeds.

### Dormant or compatibility-only application wiring

Nearly all normal `app.py` helpers have production callers. The notable seams
are narrow:

- `_release_session_start_capture` is used by tests but has no current
  application caller.
- `session_claims_execution` and `claims_execution_without_log` are older
  execution-claim helpers superseded by the structured F.3 audit. Do not revive
  them without a measured need.
- Socket event `get_status` has no current UI emitter; connection already sends
  the state snapshot. Treat it as compatibility residue, not a missing product.

The useful missed opportunities are therefore at subsystem joins—ERL into
ORIENT, canonical box workspace source, Governor consolidation—not a hidden set
of disconnected business functions.

## 6. Canonical-source ambiguities for B6

At the accepted B1 snapshot:

- root `box_ops.py` is a stale predecessor (`d6ecf68` is its last path commit)
  and differs from manifest-defined `live/box/box_ops.py`, which was updated in
  `0ef62d7`. The live copy is the B1 source; B6 should remove or unmistakably
  tombstone the competing root copy after compatibility review.
- root `db.py` and `live/db.py` are byte-identical.
- root `workspace_db_endpoint.py` and `live/workspace_db_endpoint.py` are
  byte-identical.
- `templates/governor.html` and `live/governor/governor.html` are byte-identical;
  `live/box/governor.html` differs.

B0's original drift observation remains immutable evidence even where repository
copies later converged. B6 should declare one canonical source per deployed
surface and make drift mechanically visible.

## 7. Retired egress residue

The manual explicitly retires IP-whitelist egress in favor of gunicorn on
`0.0.0.0:5001` with application-layer authentication. Nevertheless:

- `register_egress` remains in `app.py`'s `OP_ALLOWED`;
- the box route still runs fixed `ufw allow` arguments; and
- direct `app.py` startup still calls `_register_egress()`.

This is B6 active-surface cleanup, not a B1 transport alternative. Remove it
only after confirming startup topology and preserving any required museum or
compatibility evidence. Do not copy the obsolete firewall action into a new
operation.

### Documentation currency boundaries

- The accepted B1 manifests contain freeze-time lifecycle prose saying the
  candidate awaits review. Their hashes and executable contract are immutable;
  post-freeze acceptance belongs in the board, handoff, and chronological fold,
  not in a rewritten deploy object.
- `live/STATE_OF_ONTINUITY.md` is a valuable June 19 snapshot, but its older
  allowlist/firewall and operational facts are historical. Do not use it as the
  current selector without reconciling it against the board, manual, and live
  baseline.
- `live/specs/erl_decision.md` remains useful reasoning history only after its
  2026-09-09 current-source addendum is read first.

## 8. Release-block placement

| Finding | Home | Why |
|---|---|---|
| Exact B1 trusted deployment and private provider configuration | **Finish B1 now** | Already accepted; no audit finding changes its scope. |
| Honest abnormal session completion | **B3 next** | Existing critical path; do not mix with alignment recovery. |
| ERL authority, persistence honesty, lifecycle joins | **B5 inspection; B7 boot acceptance if relevant** | It concerns traversable evidence and whether orientation retrieves durable truth. Build only what an acceptance test needs. |
| Canonical app/box/database/Governor sources, legacy workspace hardening, retired-route cleanup | **B6** | These are installation reproducibility and competing-active-implementation issues. |
| Governor minimum needed by an outside operator | **B6/B9** | Reuse current routes and selectively port the preserved delta. |
| Intake residuals and compatibility helpers | **Watch/post-1.0 unless reproduced** | No current release failure establishes priority. |

## 9. Retrieval checklist for the future Control seat

Before proposing work in any area above:

1. Read this register and the current `ONTINUITY_1_0_BOARD.md`.
2. Inspect the named current source and its tests at the then-current exact SHA.
3. Check live repo/Railway/box state; do not infer deployment from Git history.
4. Search preserved branches and history for reusable deltas.
5. State which existing mechanism is being reused and which acceptance failure
   requires any new code.
6. Keep review, signoff, authorization, publication, install, restart, and deploy
   as distinct evidence-bearing transitions.

That is how the dormant wiring gets to shine without becoming an excuse to
expand the release.
