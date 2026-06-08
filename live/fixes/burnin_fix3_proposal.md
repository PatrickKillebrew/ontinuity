# Fix Proposal #3 — adversarial catch not durably surfaced (receipt #117 class)

**Status: PROPOSED design, not deployed. Operator review + sign-off (engine) and VPS hands (db.py column + endpoint) required. All investigation read-only.**

## What actually happens (grounded)
When the adversary intervenes — the Challenger formally challenges, F.3 flags a fabrication, or Parietal RESOLVES/forces a re-execution — the engine appends a formatted string to the in-memory `challenge_events` list (e.g. `"Cycle N: F.3 INSUFFICIENT_EVIDENCE — ..."`, `"Cycle N: RESOLVED — ..."`). Three things then go wrong for durability:

1. **The catch is not surfaced at the session/certification level.** 10 post-d34 `complete` sessions had ≥1 catch, including #117 (3 events). A `complete` certification carries no signal the adversary had to intervene — clean completes and complete-after-catch are indistinguishable in the session row.
2. **`challenge_count` does not count most catches — by design, not bug.** `parse_challenge_counts` only counts events containing UPHOLD/REJECT/PURSUE/ESCALATE (formal Challenger rulings). F.3 catches and Parietal resolves contain none of those, so they count as 0. Of the 10 caught sessions, 6 read `challenge_count=0`. The count measures formal challenges only; it was never meant to measure F.3/Parietal interventions, so those are invisible.
3. **The catch content is lost in the table.** The endpoint writes each raw event string via `insert_challenge_event`, which cannot parse a formatted string into columns, so it lands `ruling='UNKNOWN'` with empty `challenged_claim`/`grounds`. Across the post-boundary corpus: **62 of 74 events are `UNKNOWN`**, only 12 (UPHOLD/REJECT) preserved a ruling. The catch existence + cycle survive; what was caught does not.

So #117's catch left only a faint trace: 3 UNKNOWN events at cycle 2, `challenge_count=0`, status `complete`. The fabrication was caught and corrected live, but the durable record cannot say so.

## Design — three coordinated pieces

### A. Session-level adversarial-catch marker (the core ask)
Add a `sessions` column `adversarial_catch_count INTEGER DEFAULT 0`. In `build_session_payload`, compute it from the events:
```python
"adversarial_catch_count": len(s.get("challenge_events", [])),
```
This flags all 10 complete-after-catch sessions and distinguishes clean `complete` from complete-after-catch. A boolean view (`adversarial_catch_count > 0`) is the citation-relevant signal: "did the adversary have to intervene in a session we certified complete?" (New column needs an additive migration — the queued autonomous-additive-migration path, or a manual `ALTER TABLE sessions ADD COLUMN`.)

### B. Capture catch content (stop the UNKNOWN loss)
Parse the event-string prefix into a ruling and keep the full text as grounds, instead of UNKNOWN/empty. Lightweight version at the write boundary:
```python
def classify_event(ev):
    u = ev.upper()
    for r in ("UPHOLD","REJECT","PURSUE BOTH","ESCALATE"): 
        if r in u: return r.replace(" ","_")
    if "F.3" in u:        return "F3_CATCH"
    if "RESOLVED" in u:   return "RESOLVED"
    if "CHECKPOINT" in u: return "AUTO_CHECKPOINT"
    return "OTHER"
# insert_challenge_event: ruling=classify_event(ev), grounds=ev (full text), claim=<cycle-tag stripped>
```
Recovers a meaningful ruling for the 62 UNKNOWN events and preserves the catch text. (Cleaner long-term: change the in-memory `challenge_events` from strings to dicts `{cycle, type, claim, grounds}` at the append sites — app.py:2306, 2438, and the formal-challenge site — and have the table read the dict. Larger; recommend the lightweight parse first.)

### C. Semantics clarification (no false "fix")
Keep `challenge_count` as formal-Challenger-rulings-only (it is correct as defined). The new `adversarial_catch_count` is the all-interventions signal. Document the distinction so the `challenge_count=0`-with-events case is understood as a semantic split, not corrected into double-counting.

## Validation against corpus
- Marker A would flag exactly the 10 post-d34 complete-after-catch sessions (6 of which read `challenge_count=0` today).
- Content fix B would reclassify the 62 UNKNOWN events to meaningful rulings (F3_CATCH / RESOLVED / AUTO_CHECKPOINT / formal).

## Relationship to #2
Once #2 (persisted execution log) lands, the #117 class becomes fully reconstructable: the marker (A) says a catch occurred, and `session_executions` shows the cited result was absent from the log at the claimed cycle then present after re-execution. A + #2 together turn "a faint UNKNOWN trace" into a complete, auditable catch record.

## Operator action required
1. Review A/B/C and the strings-vs-dicts choice for B.
2. db.py: add the `adversarial_catch_count` column (additive migration) and update `insert_challenge_event` for B; apply on VPS + restart endpoint.
3. app.py: deploy the payload field (A) with the `Operator-Signoff` trailer.
4. Forward-only for content (B): past UNKNOWN rows can be re-parsed in place by a one-time UPDATE since the full event text may still live in `grounds` if present — verify before assuming; otherwise forward-only.

No deploy performed. No farm session run.
