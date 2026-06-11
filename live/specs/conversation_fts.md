# SPEC — Conversation records into the DB as queryable evidence (FTS5)

*Status: PROPOSE-ONLY (no build). Authored by worker1 (claude:opus-4.8) under CONVDB-1. Grounds: live/conversations/CONVENTION.md (what a record IS + its fields), the existing session_transcripts schema (the corpus's text-store pattern), write_receipts/sessions join keys, and the provenance-ledger lifecycle item. Inferences labeled.*

## THE GAP (the 14-02-37 evidence-channel finding)
The receipts capture the work; the sessions capture the seat. The OPERATOR layer — where direction is set, fabrications are caught, STOPs are authorized, errata originate — lives only as prose in live/conversations/*.md (CONVENTION.md). That prose is committed and cross-referenced, but it is NOT queryable: you cannot ask "find the ruling where the operator rejected the cycle-3 claim" and get a row. An operator ruling is currently unreceiptable testimony — citable by hand, not by query. This makes review findings and rulings evaporate (the review-findings-durability item) and is the same evidence-channel gap the 14-02-37 deadlock exposed: a decision with no queryable channel cannot be cited as evidence later.

## WHAT GETS INGESTED (per CONVENTION.md, not everything)
NOT the whole conversation — the OPERATOR-LAYER events CONVENTION.md already says a record captures, as discrete rows:
- DIRECTION SET — an operator directive that shaped the work.
- FABRICATION CAUGHT — an operator catching a fabricated/false claim (the receipt #22 class).
- STOP AUTHORIZED — an operator STOP/kill and its grounds.
- RULING — an operator adjudication (verbatim, per CONVENTION rule 2).
- ERRATUM ORIGIN — where an erratum started.
Each row preserves CONVENTION's invariants: redacted (rule 1), fidelity declared (rule 2: verbatim/condensed/decision-record), lineage honest (rule 3), cross-referenced to the receipts/deploys/shas it produced (rule 4).

## SCHEMA — conversation_records + an FTS5 virtual table
Mirrors the session_transcripts pattern (TEXT PK, FK to the artifact it concerns, role, content) plus CONVENTION's provenance fields. No existing FTS/virtual tables in the corpus — this is the first; it is additive (new tables only), the SAFE migration class.
```
CREATE TABLE conversation_records (
    record_id     TEXT PRIMARY KEY,           -- uuid
    record_date   TEXT NOT NULL,              -- the conversation date (YYYY-MM-DD)
    topic         TEXT,                       -- from the filename convention
    event_kind    TEXT NOT NULL,              -- direction|fabrication_caught|stop|ruling|erratum
    participants  TEXT NOT NULL,              -- 'operator; claude:opus-4.8' (lineage-honest)
    fidelity      TEXT NOT NULL,              -- verbatim|condensed|decision_record (CONVENTION rule 2)
    content       TEXT NOT NULL,              -- the ruling/directive text (verbatim for rulings), REDACTED
    -- cross-reference / join keys (CONVENTION rule 4): the walk conversation->decision->commit->receipt
    receipt_id    INTEGER,                    -- write_receipts.receipt_id this produced, if any
    session_id    TEXT,                       -- sessions.session_id this concerns, if any
    commit_sha    TEXT,                        -- the queue/commit sha
    source_file   TEXT NOT NULL,              -- live/conversations/<file>.md it was distilled from
    redacted      INTEGER NOT NULL DEFAULT 1, -- 1 = redaction-checked (CONVENTION rule 1); never commit 0
    created_at    TEXT NOT NULL
);

-- FTS5 full-text index over the searchable text. external-content table keyed to
-- conversation_records so the index stays in sync and storage isn't doubled.
CREATE VIRTUAL TABLE conversation_records_fts USING fts5(
    content, topic, participants, event_kind,
    content='conversation_records', content_rowid='rowid'
);
-- triggers keep the FTS index in sync with the base table (standard external-content pattern):
CREATE TRIGGER conv_ai AFTER INSERT ON conversation_records BEGIN
  INSERT INTO conversation_records_fts(rowid, content, topic, participants, event_kind)
  VALUES (new.rowid, new.content, new.topic, new.participants, new.event_kind);
END;
CREATE TRIGGER conv_ad AFTER DELETE ON conversation_records BEGIN
  INSERT INTO conversation_records_fts(conversation_records_fts, rowid, content, topic, participants, event_kind)
  VALUES('delete', old.rowid, old.content, old.topic, old.participants, old.event_kind);
END;
CREATE TRIGGER conv_au AFTER UPDATE ON conversation_records BEGIN
  INSERT INTO conversation_records_fts(conversation_records_fts, rowid, content, topic, participants, event_kind)
  VALUES('delete', old.rowid, old.content, old.topic, old.participants, old.event_kind);
  INSERT INTO conversation_records_fts(rowid, content, topic, participants, event_kind)
  VALUES (new.rowid, new.content, new.topic, new.participants, new.event_kind);
END;
```
PREREQUISITE (flag): confirm the box's SQLite is built with FTS5 (most are; verify via `pragma compile_options` once — the read-only diag guard blocks pragma, so this check runs box-side at migration time). If FTS5 is absent, fall back to a LIKE-scan over conversation_records.content (slower, no ranking) — the table + cross-refs still deliver queryable rows; only the ranked search degrades. INFERENCE: FTS5 is almost certainly present (default in modern SQLite builds), but the migration must check, not assume.

## INGESTION POINT
The CLOSE RITUAL already writes the conversation record to live/conversations/ (the control seat does this — a worker backfilling from commits can't see the conversation window). Add one step to the same ritual: distill the operator-layer events from that record into conversation_records rows. Two build options:
- (a) A scoped op `/op/ingest_conversation_record {source_file}` the control seat calls at close: it reads the committed live/conversations/*.md, parses the declared events, and INSERTs the rows (FTS auto-syncs via triggers). Rides the existing scoped-op + ledger pattern; redaction is re-checked at ingest (refuse to insert a row failing the credential scrub — CONVENTION rule 1 enforced in code, not just convention).
- (b) Manual: control composes the rows as part of the close ritual. Lower tooling, higher lapse risk (the same lapse class that left conversation logging dropped after one entry on June 7).
RECOMMEND (a): make redaction + ingestion machine-enforced, since CONVENTION rule 1 is a public-repo credential-safety rule and a human scrub is exactly what lapses.

## EXAMPLE QUERIES (the point of the whole thing)
```
-- find a ruling by keyword (ranked)
SELECT r.record_date, r.event_kind, r.content, r.receipt_id, r.commit_sha
FROM conversation_records_fts f JOIN conversation_records r ON r.rowid = f.rowid
WHERE conversation_records_fts MATCH 'cycle claim fabricat*'
ORDER BY rank;

-- every operator STOP and what it produced
SELECT record_date, content, session_id, receipt_id
FROM conversation_records WHERE event_kind='stop' ORDER BY record_date DESC;

-- walk a receipt back to the ruling that authorized it
SELECT * FROM conversation_records WHERE receipt_id = 22;

-- all fabrication-caught events (the receipt #22 class), newest first
SELECT record_date, content, commit_sha FROM conversation_records
WHERE event_kind='fabrication_caught' ORDER BY record_date DESC;
```

## HOW IT COMPOSES WITH THE PROVENANCE-LEDGER LIFECYCLE CHAIN
The provenance ledger (proposal->review->signoff->deploy as one logged chain) records the DECISION-to-DEPLOY lifecycle. conversation_records records the OPERATOR-DIALOGUE that drove those decisions. They share join keys (receipt_id, commit_sha, session_id), so a stranger walks: conversation_record (why) -> provenance-ledger entry (decision+signoff) -> commit (what) -> write_receipt (result), in either direction. This is the "review findings currently evaporate" item closed: a ruling caught in conversation becomes a queryable row that the provenance chain can cite. INFERENCE: ideally conversation_records.commit_sha and the provenance ledger's sha are the SAME key, so the two are one join — recommend keying them identically when both build.

## ACCEPTANCE
- A committed live/conversations/*.md record, ingested, yields rows; an FTS MATCH on a ruling keyword returns it ranked.
- A row failing the redaction check (a credential pattern in content) is REFUSED at ingest, not inserted.
- A receipt_id query returns the ruling that produced it (the walk works).
- FTS5-absent fallback: the same queries work via LIKE (unranked) — the evidence channel does not depend on FTS5 being present, only its ranking does.

## PERSISTENCE-RULE TRAIL
Read CONVENTION.md via read_repo (found at live/conversations/CONVENTION.md); confirmed session_transcripts schema, the absence of existing FTS tables, and the write_receipts/sessions join keys against the live corpus before specifying the schema.
