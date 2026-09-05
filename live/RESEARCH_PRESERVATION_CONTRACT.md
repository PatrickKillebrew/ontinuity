# ONTINUITY RESEARCH PRESERVATION CONTRACT

**Release lane:** B5-P — bounded evidence preservation before measurement  
**Status:** LIVE — Section 5 acceptance completed 2026-09-05
**Capture boundary:** session `2026-09-05_09-37-00`, write receipt `351`
**Capture version:** `ontinuity-research-evidence/1.0`  
**Database schema version:** `1.1.0`

## 1. PURPOSE AND BOUNDARY

Ontinuity's operational record is also the irreplaceable substrate described in
*Psychology of AI Data*: friction sequences, status tags, challenge events, and
retractions. Analysis can be built later. Evidence that was never captured
cannot be reconstructed later without invention.

This contract therefore requires preservation of raw evidence from new sessions before B8
measurement begins. It does **not** add behavioral scoring, psychological
interpretation, experiments, dashboards, model routing, gate decisions, access
control, or deployment behavior. It does not rewrite historical rows.

The canonical session database remains the source of truth. No parallel JSONL
research ledger is introduced.

## 2. PRESERVATION RULES

1. **Raw evidence is immutable.** Exact prompts, messages, responses,
   challenges, rulings, and dispositions are preserved as observed. A later
   correction appends a linked event; it does not erase its cause.
2. **Derived measures are versioned and replaceable.** Marker counts, friction
   aggregates, scores, and psychological interpretations are not raw evidence.
   Every future derivation must name its extractor and version and remain
   reproducible from preserved raw rows.
3. **Unknown remains unknown.** Missing historical detail is not backfilled by
   parsing, inference, a configured model label, or operator recollection.
4. **Configured identity is not authenticated identity.** Until B1/B2 bind an
   admitted actor, the occupant of an external Researcher seat is stored as
   `UNVERIFIED_PENDING_B1_B2`. A historical model string is never substituted.
5. **Secrets are excluded by construction.** Model-call records contain the
   endpoint host only—never a full URL, query string, header, API key, token, or
   credential-bearing exception. Non-secret role configuration contains model,
   provider format, host, prompt path, and configured state only.
6. **Research eligibility is an access-and-use gate.** Operational evidence is
   retained to make the system auditable even when it is not eligible for
   behavioral research. Consent and eligibility govern who may use which rows
   for research and how they must be de-identified; they are not permission to
   discard, silently alter, or falsely relabel the operational record.
7. **Pre-boundary history stays honest.** Earlier sessions retain their original
   completeness. New nullable challenge columns remain NULL on old rows; no
   claim, grounds, occupant, prompt, or provenance is manufactured for them.
8. **One session attempt is one atomic ingest.** The first committed payload
   for a session identifier wins, including an attempt that ends during
   PRE_SESSION. A retry returns `already_recorded` without adding rows, and a
   failed ingest rolls back in full before it can be retried.

## 3. REQUIRED RAW RECORDS FROM THE CAPTURE BOUNDARY FORWARD

### 3.1 Structured challenge and adjudication record

Every Challenger `CHALLENGE` preserves:

- session, cycle, and within-session sequence;
- the exact full Researcher response as `challenged_claim`;
- the exact full Challenger response as `grounds`;
- the ruling label and full untruncated ruling or disposition;
- the adjudication channel: `parietal`, `operator`, or `execution_log`;
- the legacy human-readable event string and capture version.

An escalation may produce two records: the Parietal escalation and the
operator's later disposition. Both are evidence. Existing
`challenge_events_raw` payloads remain accepted. Raw-only legacy events are
retained rather than dropped, and their unknown fields remain empty.

### 3.2 Retraction/disposition record

Every entry removed from the session Established Results Ledger by an upheld
challenge preserves:

- its exact source entry JSON and full claim text;
- the source cycle and ruling cycle;
- the append-only disposition `EXPUNGED`;
- session sequence and capture version.

This is the durable form of the existing in-memory `expunged_ledger`; it does
not modify the project-level Established Results Ledger.

### 3.3 Model-call envelope

Every in-session model call—including cycle-zero ORIENT/PRE_SESSION work and an
external Researcher mailbox turn—preserves:

- role, cycle, and within-session sequence;
- configured model string, provider format, and endpoint host only;
- exact full system prompt and SHA-256 digest;
- exact full messages JSON and SHA-256 digest;
- exact full response returned by the engine/provider adapter and SHA-256
  digest when one exists;
- `started_at`, `ended_at`, and an honest success/failure status;
- capture version.

The envelope records what the engine sent and received. The existing external
mailbox boundary strips only outer whitespace before returning a response; the
envelope preserves that exact engine-visible logical content rather than
claiming to preserve transport bytes the engine discarded. A propagated adapter
exception records `failed_exception` and an end timestamp but never exception
text, which can contain credential-bearing URLs or headers. An observed empty
string is preserved with its digest and records `failed_empty_response`, matching
the engine's existing failure semantics rather than claiming success. A logical call still
open when the final payload is frozen records `incomplete_at_snapshot`, not a
false success or permanently open final row. The envelope does not claim that a
configured label authenticates the external actor that produced a response.

Cycle-zero PRE_SESSION authorship questions sent directly through the external
Researcher mailbox are captured by the same envelope schema even though that
path intentionally bypasses provider routing.

The start reservation is session-scoped. Its session identifier and start time
exist before the first ORIENT/PRE_SESSION call. A dashboard question prompt may
retain that reservation only while it awaits its matching continuation; the
continuation consumes it once, and cancellation releases it. An exception,
external-mailbox timeout, unanswered prompt, or other terminal abort releases
the reservation in all cases. If any model call began, the attempt is first
written with status `incomplete_pre_session`, zero main-loop cycles, and no
fabricated transcript turns. Its cycle-zero envelopes remain the evidence of
what actually occurred.

### 3.4 Exact transcript companion

The existing normalized `session_transcripts.content` remains populated for
compatibility. From this capture boundary forward, each turn also stores its
full engine-visible `raw_content` and SHA-256 digest. No length truncation or
punctuation normalization is applied to that companion field. Historical rows
remain honest with NULL raw content and digest.

### 3.5 Session reproducibility manifest

Each session preserves one non-secret manifest containing:

- capture and database schema versions;
- `started_by` and instance;
- a code revision from a common deployment revision variable when exposed,
  otherwise explicit `UNKNOWN`/NULL;
- the frozen pre-session contract JSON and digest;
- configured prompt-file paths, exact contents, per-file digests, and a digest
  of the complete prompt-file manifest;
- non-secret effective role configuration;
- explicit external-occupant verification status.

Per-call envelopes remain authoritative for prompts and role configuration that
vary during a session. The manifest is the reproducibility snapshot; it is not
an identity credential.

## 4. STORAGE AND MIGRATION

The additive schema creates:

- `model_call_envelopes`;
- `session_reproducibility_manifests`;
- `retraction_events`;
- `session_executions` for deterministic execution results already emitted by
  the engine.

It adds nullable `sequence_number`, `adjudication_channel`, `raw_event`, and
`capture_version` columns to `challenge_events`, plus nullable `raw_content` and
`raw_content_sha256` columns to `session_transcripts`. It also preserves the
installed system's `adversarial_catch_count` session aggregate and behavioral
observation fields for computed signal, injected signal, randomization, and
operator-modal contact. Initialization inspects existing table shapes and adds
only absent columns. Natural unique evidence keys and first-write-preserving
inserts protect the new child rows, while the complete `/api/session` write
runs in one serialized SQLite transaction. Re-running the migration is safe.
No DROP, DELETE, type change, or historical UPDATE is permitted by this lane.

The endpoint also preserves the installed box's bounded SELECT-only diagnostic
route, append-only success/failure write receipts, execution-row ingest,
Knowtext schema default, and module-relative absolute default database path.
Root and `live/` database/endpoint copies must have the same behavior. B6 still
owns the larger canonical-location and installed-byte reconciliation.

## 5. ACCEPTANCE EVIDENCE

Before these bytes can be called live:

1. independent review confirms the author did not sign off its own work;
2. a legacy payload still writes its full raw event without truncation;
3. a new payload writes exact long challenge text, model-call envelopes, one
   manifest, and all expunged-ledger dispositions;
4. an old-schema SQLite database migrates idempotently and leaves old row bytes
   and values unchanged except for new NULL cells;
5. a secret canary placed in an API key and URL query is absent from the payload
   and every new database column;
6. hashes reproduce from the exact stored prompt, message JSON, response,
   contract JSON, and prompt-file manifest;
7. identical completed-session retries add no transcript or evidence rows, and
   an injected mid-write failure leaves no partial session;
8. a long Unicode transcript turn retains the legacy normalized content and an
   exact raw companion whose digest reproduces;
9. a raised or unanswered PRE_SESSION call writes one
   `incomplete_pre_session` attempt with zero transcript turns, releases its
   start reservation, and permits the next start; a dashboard question wait
   retains only its own token until one continuation or cancellation;
10. the installed query route remains SELECT-only, successful and failed
    ingests append receipts, execution rows participate in complete-session
    rollback, and the recovered behavioral fields survive migration and ingest;
11. a deliberately challenged specimen session can be reconstructed from the
   database without consulting a model's memory.

The first ten are code-level acceptance for B5-P. The eleventh is the live
specimen required before the capture boundary is declared operational.

### 5.1 Operational acceptance record

- Independent correction/review commit:
  `33267533e78515857d71d0c6b53a93f298ad6fe7`.
- Railway deployment `2561a8e1-7426-4a54-ab84-1710dce91d41` reached
  `SUCCESS` at that exact revision; the engine manifest later recorded the
  same observed code revision.
- The box installed the reviewed `db.py` and `workspace_db_endpoint.py` bytes,
  restarted cleanly, passed SQLite integrity, retained all 327 pre-boundary
  sessions, and preserved the 22 pre-existing table counts checked before the
  specimen. Installed SHA-256 digests were
  `3a265211a45f1cfe394316288f76473fe39fb60ff55acc31292ffcd6e0049a8e`
  and `2125b2953b66c3ab583fba947b34d4c49e2f1ea5471da37d8f97f595c25608d0`.
- The code-level suite passed 33 of 33 tests, including legacy ingest,
  migration/idempotency, atomic rollback, pre-session failure, long Unicode,
  secret-canary, exact-hash, and recovered-box-behavior cases.
- The deliberately challenged live specimen completed normally in three
  cycles. It persisted six transcript turns, fourteen model-call envelopes,
  one structured challenge, one append-only retraction, one reproducibility
  manifest, three behavioral observations, two artifacts, and receipt `351`.
- The specimen recorded one Challenge, one `UPHOLD`, and one adversarial catch.
  The Researcher retracted the unsupported 50-percent inference and separated
  evidence-capture capability from comparative-performance proof.
- All six transcript digests, all 42 per-call system/messages/response digests,
  and both stored manifest digests were independently recomputed from returned
  database content and matched. The available mailbox, diagnostic, Railway,
  and GitHub credentials were absent from the reconstructed evidence payloads.

The legacy `artifacts.content` path remains a normalized work-product view: in
this specimen it converted Unicode em dashes to ASCII `--`. The exact submitted
closing response remains preserved, digest-matched, in model-call envelope 14.
The clean artifact and forensic raw envelope are therefore distinct records;
immutable artifact revision/digest joins remain deferred under B5/B6 rather
than being falsely claimed by B5-P.

## 6. DEFERRED WORK

- authenticated actor/occupant identity: B1/B2;
- operator-event and full artifact-to-deployment joins: remainder of B5;
- explicit conversation -> session -> mailbox block -> review -> commit ->
  deployment -> receipt correlation: remainder of B5;
- provider latency, retry, token, and cost metadata: later additive telemetry,
  after defining provider-neutral fields and secret-redaction tests;
- immutable artifact revision/digest joins to exact deployed bytes: B5/B6;
- backup/restore proof and canonical installation: B6;
- behavioral metrics, interpretation, and comparative claims: B8;
- consent policy, de-identification implementation, and research-access roles:
  required before external/client rows are used for research.

No analytical conclusion follows merely from installing this capture layer.
Its claim is narrower: future sessions leave the evidence from which honest,
versioned analysis may later be performed.
