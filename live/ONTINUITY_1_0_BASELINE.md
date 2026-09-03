# ONTINUITY 1.0 — RELEASE BASELINE B0

**Observed:** 2026-09-03  
**Release block:** B0  
**Release condition:** RC-7 — Consolidated, reproducible system  
**Purpose:** establish the first evidence-bounded description of the system at the start of the completion phase. Unknown live facts are preserved as unknown rather than filled from the July record.

---

## 1. BASELINE RESULT

**Result: PARTIAL PASS.** The repository and public-site surfaces are directly verified and internally inspectable. Railway and box live-state queries are unreachable from the current ChatGPT Work network path, so deployed revisions, installed box hashes, database state, and current runtime configuration remain `UNKNOWN`. This is an access-path limitation, not evidence that either service is unavailable.

The baseline is sufficient to identify the first release dependencies and to prevent work from being selected from stale punch-list text. It is not sufficient to authorize a runtime correction or claim deployment equivalence.

---

## 2. DIRECTLY OBSERVED STATE

### Repository

| Field | Observed value | Evidence |
|---|---|---|
| Repository | `PatrickKillebrew/ontinuity` | Git remote and public repository |
| Branch | `main` | `git ls-remote` and clean clone |
| Input SHA for this baseline | `48f357c5e87e96aa7a6e103d2648864670c1df67` | `git rev-parse HEAD` after Phase-0 board commit |
| Previous completion-plan SHA | `cd6dd66e934372f9d01589d6383e147ec52fd03a` | Git history |
| Platform-succession fold SHA | `7d9436549263d43e4824fcf2cc94c5823bd82b28` | Git history |
| Runtime command | `python app.py` | root `Procfile` |
| Python syntax check | PASS | `py_compile` over engine, model client, both DB layers, box server/ops/mailbox, Governor route module, and bootstrap gate |

### Public site

`https://ontinuity.org/` responded during this baseline and serves the current verification-first homepage. It describes:

- the gate-and-contract architecture;
- interchangeable model seats;
- the two-party author/deployer separation;
- the 319-session behavioral record;
- the corpus as auditable memory;
- the Boundary De-Identifier.

This disproves the July snapshot's statement that the public homepage still primarily represented the April architecture. The public-site modernization is DONE.

### Main engine source surface

The repository-defined main engine is root `app.py`, launched by the root `Procfile`. Its source currently defines:

- external-seat routes: `/agent/start`, `/agent/stop`, `/agent/queue`, `/agent/queue_update`, `/mailbox/turn`, `/mailbox/respond`;
- resumption and diagnostics: `/agent/handoff`, `/diag/<path:endpoint>`;
- scoped courier: `/diag/op/<name>`;
- cockpit: `/` -> `templates/index.html`;
- Governor: `/governor`, `/governor/data`, `/governor/workers`;
- intake: `/intake_chat`, `/intake_capture`, `/intake_resume`;
- keyboard surface: `/kb`.

The source-defined courier allowlist contains 19 operations:

`read_journal`, `restart_workspace`, `register_egress`, `mailbox_send`, `mailbox_fetch`, `mailbox_ack`, `mailbox_peek`, `mailbox_reclaim`, `mailbox_purge`, `write_file`, `commit_self`, `read_file`, `commit_file`, `you_there`, `read_repo`, `bootstrap_gate`, `deploy`, `seed_tenant`, `backup_db`.

This count is a repository fact. It does not prove that the same source is deployed.

### Cockpit and Keys modal

`templates/index.html` contains the previously remembered interface:

- live transcript container;
- Researcher/Challenger session presentation;
- Researcher objective input and pre-session questions;
- five-role Keys and Providers modal;
- external Researcher mode;
- GitHub persistence fields;
- browser local-storage configuration;
- Socket.IO configuration and session events.

The engine stores received runtime overrides in process-global `runtime_configs`; dashboard values outrank Railway environment fallback and are lost on restart. This confirms the recorded last-save-wins drift risk. The Keys modal is an extant recovery/configuration surface, not a safe 1.0 identity architecture.

### Box source surface

The repository contains separately installable box sources:

- `live/box/file_server.py` — workspace server and blueprint host;
- `live/box/seat_mailbox.py` — persistent coordination mailbox;
- `live/box/box_ops.py` — bounded operations and deploy gate;
- `live/workspace_db_endpoint.py` / `live/db.py` — database API and schema source expected by the box installation;
- `live/shepherd_alert.py` — imported by the box server as a daemon when available.

Repository commit and box installation remain structurally separate. The current installed box bytes are not inferable from these files.

### Source fingerprints

Git blob identifiers are used because `/diag/version` reports the running `app.py` in the same format.

| Repository path | Git blob SHA |
|---|---|
| `app.py` | `3fcaaf31fe9df313d7e02b900b4a219a8a1a0b78` |
| `db.py` | `33592a574fdd9e9d54e4e3caef1f8549fea0f7b3` |
| `model_client.py` | `34a467b99eec792263a94140d806800e7a1620c8` |
| `templates/index.html` | `e025e46d761f3b8dd2fc6a36ebefc34bfd2741bd` |
| `live/box/file_server.py` | `1289a0f2b417a692773129bde8eb9f5ee29a9ef7` |
| `live/box/seat_mailbox.py` | `c58e4cb009d668ae1788f1b9cb71878438158457` |
| `live/box/box_ops.py` | `1ff93529e930b2fe7292d72acf4c9bcafe1b731c` |
| `live/governor/governor_routes.py` | `d64b1d36a96fa4490a4646f7992a1bdd49a13dcd` |
| `live/governor/governor.html` | `b87aefddaeb14dbb6c32d14d5f88c9f9b602e9db` |

These fingerprints are the comparison targets for the live probes below.

---

## 3. LAST-KNOWN LIVE STATE — NOT REOBSERVED

The September 3 succession fold records the following as live at the close of its second lap:

- MAIN healthy and idle;
- courier allowlist 19;
- Challenger `cerebras:gemma-4-31b`;
- Parietal `cerebras:gpt-oss-120b`;
- one failed-closed session `2026-09-03_14-13-03`;
- one completed session `2026-09-03_14-35-29`;
- no orphaned active session observed.

Those facts are valid historical evidence for that close. They are not substituted for current observations in this baseline.

---

## 4. LIVE FIELDS STILL UNKNOWN

| Surface | Required observation | Current state |
|---|---|---|
| Railway MAIN | deployment id, commit hash, status, restart time | UNKNOWN — current workspace cannot reach Railway engine/API path |
| Railway FARM | deployment id, commit hash, status, restart time | UNKNOWN — same access-path limitation |
| MAIN engine | `/diag/version`, `/diag/engine`, `/agent/handoff` | UNKNOWN — no current HTTP response obtained |
| Runtime roles | effective URL/model per role after process-global overrides and env fallback | UNKNOWN — repository defaults are intentionally blank |
| Box | installed hashes for `file_server.py`, `seat_mailbox.py`, `box_ops.py`, DB endpoint/schema files | UNKNOWN — courier unreachable from current workspace |
| Database | schema versions, table inventory, session counts/statuses, latest receipts | UNKNOWN — box query relay unreachable |
| Mailbox | queued/claimed/done counts, expired leases, orphaned claims | UNKNOWN — box courier unreachable |
| Governor | authenticated `/governor/data` and `/governor/workers` payloads | UNKNOWN — source exists; deployed authenticated response not observed |
| Cockpit | live engine-root rendering and Socket.IO behavior | UNKNOWN — source exists; Railway root not observed now |

**Access-path finding:** GitHub transport and the public `ontinuity.org` site work from this workspace. Direct requests to `web-production-7eaf8.up.railway.app` stalled, and the ordinary web-access surface rejected that Railway hostname as unsafe. A later Railway API attempt was denied by the workspace network-approval layer. No HTTP status was received from Ontinuity; therefore this does not establish an application outage or an authentication failure.

---

## 5. REPOSITORY DRIFT AND AMBIGUITY FOUND

### Database schema copies differ

Root `db.py` and `live/db.py` are not byte-equivalent. Root `db.py` contains later behavioral fields absent from `live/db.py`:

- `computed_signal`;
- `injected_signal`;
- `randomized_flag`;
- `modal_touched`.

Root also defaults a missing Knowtext schema label where `live/db.py` does not. The box server imports a sibling `workspace_db_endpoint` and `db` from its installed directory, so the running box schema source cannot be determined from repository location alone. B0 therefore records a canonical-source defect: **the repository has two plausible DB implementations and does not mechanically declare which exact bytes are installed.**

### Governor copies exist in three places

Governor HTML exists at:

- `templates/governor.html` — the file root `app.py` actually serves at `/governor`;
- `live/governor/governor.html` — the development/relay package;
- `live/box/governor.html` — a box-side copy.

The main engine's runtime canonical file is unambiguous from source (`templates/governor.html`), but the other copies can drift and their intended lifecycle is not declared.

### Runtime model state is intentionally non-reconstructible from Git

All role defaults in root `app.py` are blank. Effective configuration is a merge of process-global dashboard overrides and Railway environment values. Git cannot establish current staffing. This is correct for secret custody but incomplete for release observability; a safe diagnostic must report non-secret role lineage/model identifiers and configuration source without exposing keys.

---

## 6. EXISTING MECHANISMS THAT SHOULD CLOSE THE UNKNOWN FIELDS

No new transport architecture is required. The repository already contains the relevant reads:

- `/diag/version` — running engine `app.py` Git blob SHA;
- `/diag/engine` — current session state;
- `/agent/handoff` — both engine states, queue head, receipts, external mailbox;
- `/diag/op/read_file` — bounded installed-file read;
- `/diag/op/read_journal` — box service evidence;
- `/diag/op/mailbox_peek` — mailbox state;
- `/diag/api/health` and `/diag/api/query` — schema and record evidence;
- Railway GraphQL `variables(...)` and deployment queries — service configuration and revision evidence.

The remaining task is to run these existing reads from an allowed network surface and append the returned identifiers/hashes. Failure to reach them from one ChatGPT workspace should be treated as an operator-access-path defect only if the same limitation affects the intended 1.0 Control surface.

---

## 7. B0 DISPOSITION

- **Claim tested:** Can the completion phase start from one truthful system map rather than the July snapshot or historical handoff?
- **Evidence read:** current Git `main`; current source; Phase-0 release board; public site; September succession fold; operating manual and handoff.
- **Change made:** created the release board; converted old pending sections to historical status; advanced the handoff; created this baseline.
- **Test result:** PARTIAL PASS — repository/public baseline complete; authenticated live equivalence outstanding.
- **New debt:** none. Two pre-existing drift seams are now explicit: DB-source duplication and Governor-copy duplication.
- **State left:** no runtime, configuration, box, schema, mailbox, or deployment mutation; documentation-only repository changes.
- **Next dependency:** complete the authenticated observations using the existing endpoints, then begin B1 capability admission and B3 fail-closed completion as the first build lanes.

The baseline is amended in place when the missing live evidence is obtained. It must not be marked PASS until deployed engine and box fingerprints are compared with this repository record.
