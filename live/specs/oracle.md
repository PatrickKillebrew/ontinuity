# SPEC — The Oracle (a corpus-grounded, refuse-to-guess answering seat)

*Status: PROPOSE-ONLY (not built, not deployed). Authored by worker22 (claude:opus-4.8) under the ORACLE-SPEC task dispatched by control (mailbox msg f5f8fff5). Grounds: live/OPERATING_MANUAL.md "THE ORACLE" design section (lines 222–235, proposed 2026-06-19); spec format/rigor matched to live/specs/verified_bootstrap_gate.md; courier allowlist + mailbox contract grounded in OPERATING_MANUAL.md lines 55, 110, 117, 123. Do not commit or deploy from this file; it specifies the build for operator sign-off.*

*REVISION 1 (worker22, claude:opus-4.8, under correction task msg 0971f1f2): applied worker11's review finding (review_finding msg 9a55cb28). DEFECT: §3.2's handshake passed corr_id/citations/confidence as top-level message fields, but live seat_mailbox.py mailbox_send (verified at L177-209) persists a FIXED column set and silently drops unknown body keys — so corr_id was never stored and the RECEIVE step's corr_id match could never succeed; a builder following the spec literally would ship a silently-broken handshake. CORRECTION (control's chosen direction, Option B): make corr_id/citations/confidence first-class nullable columns via an additive-safe migration (mirroring the NOSELF-1 author_seat/author_lineage migration verified at seat_mailbox.py L78-86), and teach mailbox_send + the fetch/peek return path to persist and return them. worker22 is the AUTHOR of this correction; per no-self-sign-off a THIRD seat (not worker22, not worker11) must sign off before control commits. Verified against live live/box/seat_mailbox.py this revision, not assumed.*

## 1. PROBLEM (grounded)
The recurring failure across the record: a seat reasons from the boot packet's SHORTHAND or its training PRIORS instead of the grounded corpus, and circles (OPERATING_MANUAL.md L223). The historical recovery is MANUAL and operator-bottlenecked — on 2026-06-19 a fresh seat 403'd for an hour guessing the vault-read query and an older, better-grounded control had to stop and explain it (OPERATING_MANUAL.md L223). That manual errand is the cost the Oracle removes: it makes grounded recovery a STANDING SERVICE instead of an operator interrupt. The Oracle is the guessing-squelch principle delivered as a service (OPERATING_MANUAL.md L233).

The distinction this whole system rests on (THE_PARADIGM.md): training data is for CAPABILITY; never for Ontinuity-facts. Where priors and corpus disagree, the corpus wins. The Oracle is the on-demand retrieval surface that lets a circling seat replace a guess with a grounded read without waking the operator.

## 2. WHAT IT IS (from the manual — not redefined here)
A hidden, READ-ONLY, corpus-grounded answering seat (OPERATING_MANUAL.md L225). It is NOT a worker: it never acts, never deploys, holds no task, and holds no credentials beyond read access. It is NOT user-facing Q&A. It is the LIVING MANUAL made POLLABLE — a service other seats call, addressed like any seat (to_seat "oracle"), never a place the human goes (OPERATING_MANUAL.md L231). Its trustworthiness is the honesty contract: it answers FROM the corpus with verified-not-assumed discipline, and where the corpus is silent it says so rather than papering the gap. An Oracle that guesses is just another circling seat (OPERATING_MANUAL.md L229).

## 3. RESOLVED OPEN QUESTIONS

### 3.1 PROCESS vs CHAT seat — RESOLVED: the Oracle MUST be an API/engine process, not a chat-window seat.
The crux is the no-self-poll invariant: a chat-window seat is dormant between turns and acts ONLY when its conversation is given a turn; no software can wake it — only an operator nudge can (OPERATING_RUBRIC.md HONEST CEILINGS; THE_PARADIGM.md HONEST CEILINGS; verified_bootstrap_gate.md CHECK 6 invariant (a)). A chat-window Oracle would therefore sit unanswered until the operator nudged it — which reintroduces the exact operator-interrupt bottleneck the Oracle exists to remove (OPERATING_MANUAL.md L231, "the human-going-to-fetch IS the manual bottleneck"). An asking seat that pings a dormant chat Oracle gets silence, not an answer.

The only substrate that can answer on-demand is one that polls/wakes itself — an API/engine instance, the pattern the farm already proves (OPERATING_RUBRIC.md PARALLELIZATION AMENDMENT; THE_PARADIGM.md "seats that poll/wake themselves = API/engine-instance seats"). RECOMMENDATION: build the Oracle as a long-running engine process (a third Railway service, or a loop colocated with the farm) that long-polls its own mailbox via the existing you_there op and replies within the same wall-clock window the asking seat is waiting. Model tier: this is a JUDGMENT-load-bearing role (it is the reliability boundary for grounding), so it runs on a frontier model for the answering step, consistent with THE_PARADIGM.md model-tiering (frontier where judgment is load-bearing). A cheaper model MAY do first-pass retrieval/citation assembly, with the frontier model gating the honesty contract — but that optimization is deferred; v1 is frontier end-to-end.

### 3.2 INVOCATION — seat-to-seat via the mailbox; exact contract below.
The asking seat sends a mailbox message addressed to the Oracle and then waits on a reply addressed back to itself. This reuses the live mailbox ops (mailbox_send / mailbox_fetch / you_there / mailbox_ack, OPERATING_MANUAL.md L55, L110) with two NEW kinds — `question` and `answer` — that must be added to the kind vocabulary. Critically, you_there today returns only task/proposal (WORKER_MANUAL.md "WORK ONLY WORK KINDS"); the Oracle process must long-poll for kind=`question` specifically, so the build adds `question` to the set the Oracle's poll claims, and `answer` to what an asking seat's receive step reads. A `question`/`answer` is NOT a work kind for ordinary workers — only the Oracle claims questions, and only the asking seat reads its own answer.

ASK (asking seat -> Oracle):
```
POST {engine}/diag/op/mailbox_send?diag_key=... body:
{ "from_seat": "<asker>", "to_seat": "oracle", "kind": "question",
  "from_lineage": "<harness:model>",
  "body": "<the confusion, stated plainly: what I am trying to ground and what I currently believe>",
  "corr_id": "<uuid the asker generates>",          # correlation id, so the asker can match the reply
  "ref": "<optional: the file/path/op the question concerns>" }
```
ORACLE POLL + ANSWER (Oracle process):
```
loop: msg = POST {engine}/diag/op/you_there body {"seat":"oracle","roles":["oracle"],"kinds":["question"],"wait_seconds":<=60}
      if msg: ground the answer (read surface §3.3), then
      POST {engine}/diag/op/mailbox_send body:
      { "from_seat":"oracle", "to_seat": msg.from_seat, "kind":"answer",
        "corr_id": msg.corr_id,                        # echoes the asker's corr_id
        "body": "<grounded answer OR 'not in the corpus; nearest grounded thing is X'>",
        "citations": [ {"source":"live/OPERATING_MANUAL.md","loc":"L222-235"}, ... ],
        "confidence": "grounded" | "nearest" | "absent" }
      then mailbox_ack the question.
```
RECEIVE (asking seat collects its answer):
```
reply = POST {engine}/diag/op/you_there body {"seat":"<asker>","roles":["<asker>"],"kinds":["answer"],"wait_seconds":<=60}
        match reply.corr_id == the corr_id I sent; if no match in budget, the asker PARKS the question
        (notes it to control) rather than proceeding on a guess — silence from the Oracle never licenses a guess.
```
NOTE on field persistence (worker11 finding, REVISION 1): corr_id, citations, and confidence are NOT body-embedded text — they are first-class columns added to seat_mailbox by build step 1 (§5), because live mailbox_send persists only a fixed column set and silently drops unknown body keys (verified, seat_mailbox.py L177-209). mailbox_send must read and persist these fields, and the fetch/peek return path must SELECT and return them, or the corr_id match below can never succeed. This is the buildability fix that makes the handshake real rather than silently-dropped.

NOTE on substrate asymmetry (honest): the asking seat may itself be a dormant chat seat. A chat asker can SEND a question and, within the SAME turn, you_there-wait up to 60s for the answer — that works because the Oracle (a process) answers fast. What a chat asker cannot do is receive an answer that arrives AFTER its turn ends. So the contract requires the Oracle to answer within one long-poll window; if it cannot (heavy question), it returns an immediate `answer` with confidence="absent"/"deferred" and a pointer, never leaving the chat asker hanging across a turn boundary. The corr_id makes a late answer recoverable by control if needed.

### 3.3 KNOWLEDGE ACCESS (read surface) — read-only across every corpus layer; no write/deploy/credential beyond read.
The Oracle reads, authoritatively and read-only, the full corpus infrastructure (OPERATING_MANUAL.md L227, L235):
- PUBLIC repo `live/` — manual, rubric, paradigm, specs, queue, session folds. Read via authed api.github.com (Accept: application/vnd.github.raw) using a READ-ONLY GitHub token; raw-CDN-cachebust only as the rate-limit fallback (WORKER_MANUAL.md read_repo source order).
- PRIVATE repo `projects/*/mini_corpus.md` — via the INTAKE_GITHUB_TOKEN vault variable (the credential already scoped to the private intake repo per system memory; OPERATING_MANUAL.md L235 names this token as the private-read path). READ ONLY.
- RAW INTAKE `sessions/` and the Synapse archive — same repos.
- THE LIVE CORPUS DB — GET {engine}/diag/api/query (read-only SELECT only; OPERATING_MANUAL.md L55 "Read corpus (read-only SELECT)"). The Oracle issues SELECTs only; it never writes.
CREDENTIAL BOUNDARY (hard): the Oracle holds ONLY read tokens (a read-scoped GitHub PAT + INTAKE_GITHUB_TOKEN read use + the diag_key for SELECT/you_there/mailbox_send). It holds NO commit/deploy token, never calls write_file/commit_file/commit_self/deploy, and never seeds tenants. Custody of even the read tokens stays in the operator's vault and is injected as process env, never written to any committed file (no-credentials rule; this repo and the spec are public).

### 3.4 THE TRIGGER (the crux) — RECOMMEND a forcing wrapper, NOT self-noticing.
The manual leaves this open: self-noticed circling vs a wrapper that watches for repeated-failure (OPERATING_MANUAL.md L235). RECOMMENDATION: a FORCING wrapper, because self-noticing is structurally weak — it relies on the SAME judgment that is already failing. A seat deep enough in a priors-loop to need the Oracle is, by definition, the seat least able to notice it is looping; asking it to self-trigger is asking the failure to diagnose itself (THE_PARADIGM.md: "Precision prevents; the gate only catches" — the architecture is the fix, not a promise of better self-monitoring).

The forcing trigger does NOT depend on the seat noticing. Two composable mechanisms, in priority order:

(a) REPEATED-FAILURE DETECTOR (primary, automatic). The relay-courier already logs every op to operations_ledger with status (OPERATING_MANUAL.md scoped-ops audit spine; verified_bootstrap_gate.md §5 schema: op_id, operation, caller, args, result, status, started_at). A lightweight watcher (sibling to the shepherd, shepherd.py/shepherd_alert.py exist in live/) scans a seat's recent ledger rows; on N consecutive failures of the same operation by the same caller within a window (proposed N=3, the same "3-bounce" escalation threshold already used for close-refusal, agent_queue FIFTH CYCLE), it INJECTS a kind=question to the Oracle on that seat's behalf AND a mailbox note to the seat: "you have retried <op> 3× — the Oracle says: <grounded answer>." The seat is handed the grounded answer without ever having had to notice it was circling. This is the part that actually fixes the control-seat low-effort default: the default no longer relies on the seat choosing to ground itself.

(b) GATED ASK ON HIGH-RISK MOVES (secondary, structural). For a narrow set of known-trap operations — the ones the record shows seats repeatedly guess wrong (the vault-read query shape; "is this op in the allowlist"; "repo-commit vs box-install"; api.github.com vs raw-CDN grounding) — the boot packet instructs the seat to ASK the Oracle BEFORE the first attempt, not after failing. This turns the Oracle from a recovery service into a prevention service for the specific moves that have a documented loss history, consistent with "precision prevents; the gate only catches."

Self-noticing (a seat voluntarily asking when it feels itself drift) is RETAINED as a third, weakest path — useful but never the load-bearing one. The wrapper (a) carries the load.

DEPENDENCY (honest): the repeated-failure detector is only as good as operations_ledger.caller being trustworthy. Today caller is self-asserted under the shared DIAG_KEY (verified_bootstrap_gate.md §5). The detector still works on self-asserted caller (a circling seat names itself honestly in the common case), but per-identity keys (PUNCH_LIST item "Seat registry / identity primitive", which absorbs the per-identity-keys work; also stubbed in bootstrap-gate step 2) make the trigger attributable rather than best-effort. The Oracle ships before that lands; the detector is honest about being keyed on self-asserted caller until then. This seam is deliberately LEFT UNMERGED: the Oracle's ship date must not be coupled to the per-identity-key registry build (a separate HIGH item). The Oracle ships on self-asserted caller and says so; identity-attribution upgrades it later without blocking it.

AUDIT RATIONALE for first-class columns (REVISION 1, control's Option B): making confidence and citations queryable COLUMNS rather than body-embedded text lets the Oracle's own answers be audited — confidence distribution (how often grounded vs nearest vs absent), citation coverage, and refuse-vs-answer rate become SELECTable metrics. This is consistent with the system's audit-everything ethos (the operations_ledger spine) and feeds the forcing-trigger detector (§3.4a) a richer signal: a seat repeatedly receiving confidence="absent" on the same topic is itself evidence of a corpus gap to fix, not just a circling seat to rescue.

## 4. THE HONESTY-CONTRACT SYSTEM PROMPT (draft)
```
You are the Oracle: a read-only, corpus-grounded answering seat in the Ontinuity system.
You exist to stop other seats from guessing. You hold no task, deploy nothing, write nothing,
and hold no credential beyond read access.

YOUR ONE RULE: answer ONLY from the corpus you can read, and CITE where each claim comes from
(file + line, or table + query). If the corpus does not answer the question, say exactly:
"That is not in the corpus. The nearest grounded thing is: <X, with citation>." — and stop.
Never fill a gap with a plausible guess. A guess from you is worse than silence, because the
seat asking you is trusting you precisely BECAUSE you refuse to guess. An Oracle that guesses
is just another circling seat.

Use your training data ONLY for capability — parsing, reading, language. NEVER for facts about
how Ontinuity works. Every Ontinuity-fact in your answer must trace to a corpus read you actually
performed this turn (read_repo / read_file / a SELECT). Where your priors and the corpus disagree
about this system, the corpus wins, every time. If you did not read it this turn, you do not know it.

When you answer:
- Lead with the grounded answer, then the citations, then confidence: "grounded" (corpus directly
  answers), "nearest" (corpus is adjacent, you are extrapolating and SAYING SO), or "absent"
  (corpus is silent — say so plainly).
- Be concise. Quote the corpus where exact wording is load-bearing (e.g. an op name, a query shape).
- Never invent a file path, a line number, an op name, a column, or a query you did not verify.
- If the question is ambiguous, say what you'd need to disambiguate; do not answer a guessed version.

You never act on the system. You never advise a deploy. You report what the corpus says and where.
```

## 5. BUILD SEQUENCE (proposed, operator-gated — DO NOT deploy from this spec)
1. Mailbox schema + contract changes (box-side seat_mailbox.py), as ONE additive-safe migration set:
   (a) Add `question` and `answer` to the kind vocabulary — extend `_KINDS` (seat_mailbox.py L40). Do NOT widen the global `_WORK_KINDS` (L461, currently {task, proposal}): that filter governs what ordinary draining workers claim, and questions/answers must NOT be drained by general workers. Instead the Oracle's poll and the asker's receive pass a per-call `kinds` filter (next item).
   (b) Additive-safe column migration: ALTER TABLE seat_mailbox ADD COLUMN for `corr_id`, `citations`, `confidence` (all nullable TEXT; citations stored as JSON text), wrapped in the same idempotent try/except ALTER pattern as the NOSELF-1 author_seat/author_lineage migration (verified seat_mailbox.py L78-86). Nullable + no rewrite of existing rows = SAFE class.
   (c) Teach mailbox_send (L177-209) to read corr_id/citations/confidence from the body and INCLUDE them in its INSERT column list (today they would be silently dropped — this is the worker11 defect fix). Teach the fetch return path (the SELECT + cols mapping at L265/268 and L499/502) AND mailbox_peek (L348/354) to SELECT and return the three new columns, or they exist but never come back.
   (d) Add a per-call `kinds` filter to you_there/mailbox_fetch so the Oracle long-polls claiming only kind=`question` and an asking seat receives only its own kind=`answer`. (The existing correlated-fetch `reply_to` path at L319 is the sibling precedent for targeted retrieval; the new corr_id column is the answer-side correlation handle.)
   INSTALL: box-side changes go live via write_file + restart_workspace (hands-free). This is the BOX-INSTALL half only. If any NEW courier op or OP_ALLOWED surface is required, that is a SEPARATE commit + deploy step — box install and the allowlist entry are two distinct steps, never one (new-box-op invariant, OPERATING_MANUAL.md L123). The schema/send/fetch edits here touch existing ops, so they need the box install; confirm whether the per-call kinds filter requires any courier-surface change and, if so, commit+deploy it separately.
2. Stand up the Oracle process: a long-running engine instance (third Railway service or farm-colocated loop) that long-polls you_there for kind=question on seat "oracle", grounds against the §3.3 read surface, and replies kind=answer with citations. Read-only credentials injected as process env from the operator vault.
3. Wire the repeated-failure detector (§3.4a) as a shepherd-sibling watcher over operations_ledger; on N=3 same-op same-caller failures, inject a question + deliver the answer to the seat.
4. Teach the boot packets (WORKER_BOOT_PACKET.md, CONTROL packets) the gated-ask-on-high-risk-moves rule (§3.4b) and the ask/receive contract (§3.2). Contract-doc currency: this change touches the worker contract, so WORKER_MANUAL.md + the boot packet + THE_PARADIGM.md update in the same close (OPERATING_MANUAL.md L77).
5. Corpus-writing discipline backstop (HARD PREREQUISITE, OPERATING_MANUAL.md L233): the Oracle is only as good as the corpus is current. The build MUST pair with the close-ritual obligation that every hard-won path is written to the corpus the moment it is learned. An Oracle over a stale corpus is a confident guesser.

## 6. ACCEPTANCE (how to prove it works)
- ABSENT-HONESTY: ask the Oracle something demonstrably not in the corpus; it returns confidence="absent" with a "nearest grounded thing" pointer and NO invented answer. (This is the load-bearing test — a guess here fails the whole concept.)
- GROUNDED-CITATION: ask a question the corpus answers (e.g. "is seed_tenant in the allowlist and what does it do"); the Oracle returns the correct answer WITH a citation to OPERATING_MANUAL.md L55, and the cited line actually says it.
- ROUND-TRIP: an asking seat sends kind=question with a corr_id, the Oracle answers kind=answer echoing that corr_id within one you_there window, the asker matches it. A wrong/missing corr_id is not accepted as the answer.
- FORCING-TRIGGER: simulate 3 consecutive same-op failures for a caller in operations_ledger; the detector injects a question and delivers the grounded answer to the seat WITHOUT the seat self-reporting. (Proves the trigger does not depend on the seat noticing.)
- CREDENTIAL BOUNDARY: confirm the Oracle process can read public live/, private mini_corpus.md (via INTAKE_GITHUB_TOKEN), and run a SELECT — and that it has NO path to write_file/commit/deploy (attempt one; it must be absent, not merely declined).
- NO-STALE-ANSWER: the Oracle reads via authed api.github.com, not raw CDN, for grounding reads (WORKER_MANUAL.md read_repo source order); confirm a freshly committed corpus line is visible to the Oracle on the next ask.


## 7. CARRIED FINDINGS (not part of the Oracle build — do not lose)
- MANUAL-CURRENCY DRIFT (worker11 side finding, verified by worker22 against live app.py L3587): OPERATING_MANUAL.md L55 states the courier allowlist is "17 ops", but live OP_ALLOWED holds 19 — it adds `mailbox_purge` and `backup_db`. This is a manual-sync task (the bootstrap gate CHECK 1 would FAIL on this count mismatch), NOT part of the Oracle build. Flagged for control to fix in a manual-currency commit. Recorded here so it is not lost between seats.
- PUNCH_LIST REFERENCE RESOLVED (control, at commit): the punch list is NOT numbered. Per-identity keys is the item named "Seat registry / identity primitive (auto-naming + per-identity keys, unified)" (HIGH), which explicitly absorbs the separate "Per-identity keys (derive-identity-from-key)" IN-PROGRESS item. The "#42" the spec originally cited is the DISTINCT "Password-unlocked vault bootstrap" item (a KDF vault, not the key registry). §3.4 now references the registry item by NAME, not number. Resolved 2026-06-29.
