# SPEC — /agent/handoff (one-call live resumption state)

*Status: PROPOSE-ONLY (engine route in app.py — operator applies + deploys). Authored by worker1 (claude:opus-4.8) under HANDOFF-1. Grounds: the live /diag routes read from app.py via /op/read_repo (the diag-key gate, the /diag/engine local-state builder, the /diag/api/query corpus path) + the confirmed write_receipts / seat_mailbox / external_mailbox shapes. The seat-layer sibling of the bootstrap gate: the gate proves a seat is oriented; handoff GIVES it the state to orient ONTO in one call instead of many.*

## PURPOSE
A fresh or recohering seat currently boots by making many calls: /diag/engine on MAIN, /diag/engine on FARM, a corpus query for receipts, a queue read, a mailbox peek. /agent/handoff returns all of it in ONE keyed call, so the open ritual / cold-boot has a single authoritative resumption snapshot. It composes existing, proven data sources — it introduces no new data, only one assembly point.

## ROUTE + AUTH
- `GET /agent/handoff` (read-only; no mutation).
- Auth: the SAME diag-key gate as /diag (app.py ~3269): `request.headers["X-Diag-Key"] == DIAG_KEY` OR `request.args["diag_key"] == DIAG_KEY`, 503 if DIAG_KEY unset, 401 if mismatch. Reuse verbatim — do not invent a new key.
- Optional query arg `?include_farm=1` (default on): also fetch the OTHER engine's state cross-HTTP. The two engines (MAIN web-production-7eaf8, FARM ontinuity-farm-production) each serve their own /agent/handoff; each reports its OWN active_session locally and fetches the peer's /diag/engine for the peer line (a peer fetch failure degrades gracefully to {error} for that engine, never 500s the whole call).

## EXACT JSON SHAPE
```
{
  "ok": true,
  "generated_at": "<iso8601>",
  "engines": {
    "main": {                       # this engine's active_session, built LOCALLY (same fields as /diag/engine)
      "running": false, "cycle": 0, "waiting_for_input": false,
      "input_type": null, "started_by": "dashboard", "stopped_by": null,
      "finalizing": false, "contract_criteria": 0
    },
    "farm": { ... }                 # peer via GET {FARM}/diag/engine?diag_key=... ; or {"error": "..."} if unreachable
  },
  "queue_head": {                   # the single current next-seat action (oldest queued WORK item for any_worker)
    "block_id": "PUNCHAUDIT-1", "kind": "task", "from_seat": "control",
    "created_at": "<iso>"           # null if queue empty
  },
  "open_turns": {                   # what is waiting for a seat right now
    "external_mailbox": {           # the Researcher-seat turn, if one is posted + waiting
      "waiting": false, "turn_id": 0, "kind": null, "cycle": 0, "session_id": ""
    },
    "seat_mailbox_queued": [        # per-seat queued counts (task/proposal = claimable work; note/result = chatter)
      {"to_seat": "any_worker", "queued": 1}, {"to_seat": "control", "queued": 4}
    ]
  },
  "latest_receipts": [              # most recent writes, newest first (the join key for provenance)
    {"receipt_id": 330, "session_id": "2026-06-10_18-24-37", "outcome": "ok"},
    {"receipt_id": 329, "session_id": "2026-06-10_17-26-49", "outcome": "ok"},
    {"receipt_id": 328, "session_id": "2026-06-10_02-57-00_farm", "outcome": "ok"}
  ]
}
```

## WHICH EXISTING SOURCES IT COMPOSES (no new data)
1. engines.main — built LOCALLY exactly like the `base == "engine"` branch of diag_relay (app.py ~3309): reads active_session running/cycle/waiting_for_input/input_type/started_by/stopped_by/finalizing/contract_criteria. No DB hit.
2. engines.farm — `http_requests.get(f"{FARM_URL}/diag/engine?diag_key={DIAG_KEY}", timeout=10)`, wrapped so a failure yields {"error": ...} not a 500. (FARM_URL is the peer engine base; INSTANCE_NAME already distinguishes main/farm in /diag/egress, so the route knows which peer to fetch.)
3. queue_head — one corpus query (the workspace DB the engine already queries via call_workspace_query / the /diag/api/query path):
   `SELECT block_id, kind, from_seat, created_at FROM seat_mailbox WHERE status='queued' AND to_seat='any_worker' AND kind IN ('task','proposal') ORDER BY created_at ASC LIMIT 1`
4. open_turns.external_mailbox — read the in-memory external_mailbox dict (waiting, turn_id, kind, cycle, session_id) — same source /mailbox/turn serves (app.py ~3236). No DB hit.
5. open_turns.seat_mailbox_queued — one query:
   `SELECT to_seat, COUNT(*) FROM seat_mailbox WHERE status='queued' GROUP BY to_seat`
6. latest_receipts — one query:
   `SELECT receipt_id, session_id, outcome FROM write_receipts ORDER BY receipt_id DESC LIMIT 3`

All three corpus queries are read-only SELECTs that pass db_query_guard and go through the existing workspace-query path; no new DB surface.

## HOW IT PAIRS WITH THE BOOTSTRAP GATE (seat-layer siblings)
- The bootstrap gate (live/specs/verified_bootstrap_gate.md) PROVES a seat is oriented: it independently checks manual/queue/corpus/hands/engine/mechanics and returns NOT ORIENTED on any failure.
- /agent/handoff DELIVERS the state a seat orients onto in one call. The gate's CHECK 5 (ENGINE) and CHECK 2 (QUEUE) read exactly what handoff returns — so a seat can call handoff ONCE, then the gate ratifies the snapshot, then the seat reasons. Handoff is the efficient fetch; the gate is the verification. They are complementary, not redundant: handoff without the gate is unverified state; the gate without handoff is many calls.
- INFERENCE (labeled): handoff could become the data source CHECK 5/CHECK 2 read from, collapsing several gate probes into one — a natural follow-up once both are live, not required now.

## WHERE IT GOES
Engine app.py, a new GET route alongside /diag and /mailbox/turn. Read-only, diag-key gated, composes existing sources. Operator: /diag/engine check, add the route, commit with Assisted-by trailer, deploy. PROPOSE-ONLY — no deploy from this file. Staged at live/specs/agent_handoff.md.

## PERSISTENCE-RULE TRAIL
Read the live /diag routes (diag_relay auth + engine branch, external_mailbox, /mailbox/turn) from app.py via /op/read_repo; confirmed write_receipts schema + the queue-head/open-turns/receipts queries against the live corpus via /diag/api/query before specifying their exact text.
