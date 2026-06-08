# Fix Proposal #4 — INTEGRITY: Challenger death silently produces an unreviewed cycle

**Status: PROPOSED, not deployed. Operator review + sign-off trailer required. All investigation read-only.**

## The hole (confirmed by inspection)
The main Challenger call is `b_response = call_model("model_b", ...)` followed by `if b_response:` with **no else branch**. `call_model` returns None only after its internal retries, so a None here is a real provider death. When it happens, the entire `if b_response:` block is skipped: no Challenger turn, no tag, no assessment, no challenge handling — and execution falls straight through to the continue section and the next cycle. The Researcher's claim for that cycle is never reviewed.

Unlike a Researcher death (which sets `incomplete_model_dead` and breaks), a Challenger death is silently swallowed: the session continues and can reach a clean SESSION_END and write `complete`, having contained one or more cycles the adversary never reviewed. That is a direct breach of the core guarantee — no Researcher claim reaches certification without adversarial review.

## Corpus scope
Rare today: 2 silent B-less cycles (Researcher emitted CONTINUE, no Challenger turn) across 2 sessions; **1 of those closed `complete`** (`2026-06-08_02-28-30`, the flag-on acceptance — unreviewed cycle 14). Low-frequency now, but it scales directly with Challenger-provider instability (the glm-4.7 read-timeout issues already on record), and a single clean completion containing an unreviewed claim is enough to undermine the credential.

## Design — record the death, gate the certification (3 edits, drafted + syntax-checked)
Mirrors the certified-close gate (#1) philosophy: don't try to recover the cycle, gate the OUTCOME so an unreviewed cycle cannot certify clean.

1. **Session init** — track unreviewed cycles:
```python
active_session["unreviewed_cycles"] = []
```

2. **At the Challenger call** — record the death durably (sibling guard before the existing `if b_response:`):
```python
if not b_response:
    _cyc = active_session["cycle"]
    active_session.setdefault("unreviewed_cycles", []).append(_cyc)
    active_session["tag_sequence"].append(f"Cycle {_cyc} B: NO_REVIEW")
    active_session["challenge_events"].append(
        f"Cycle {_cyc}: CHALLENGER_DEAD — cycle unreviewed (Challenger provider death)")
    socketio.emit('routing_action', {'type': 'error',
        'message': f'STATUS: Challenger death at cycle {_cyc} — Researcher claim unreviewed; session cannot certify complete.'})
```

3. **Close gate** — extend the #1 `_final_status` so an unreviewed cycle downgrades out of `complete`:
```python
_unreviewed = bool(s.get("unreviewed_cycles"))
_final_status = (
    _end_status if _end_status != "complete"
    else "incomplete_challenger_dead" if _unreviewed
    else "complete" if _has_close
    else "incomplete_no_close")
```

The death is now durably visible (NO_REVIEW tag + CHALLENGER_DEAD challenge_event), and any session with an unreviewed cycle lands `incomplete_challenger_dead` instead of `complete`. Complementary to #1: #1 catches no-close exits, this catches unreviewed cycles; a Challenger death followed by a later clean SESSION_END would pass #1 but is correctly downgraded here.

## Design choice noted for review
This is the *gate-and-continue* option: a single Challenger flake doesn't kill the session, but the session can never certify clean if any cycle went unreviewed. The stricter alternative is *break-on-death* (treat Challenger death like Researcher death — break immediately with `incomplete_challenger_dead`). Gate-and-continue is recommended: it preserves recoverable sessions (Challenger may answer the next cycle) while still refusing a false clean completion. Operator's call.

## Verification
- Corpus: the gate would reclassify the 1 affected `complete` session (#54) to `incomplete_challenger_dead`; a backfill is optional since it's a single historical acceptance session, not the burn-in ratio.
- Post-deploy: reproducing a live Challenger death is non-deterministic; the fix is validated by inspection + the close gate's deterministic logic. A controlled verification session confirms no regression on a normal reviewed close.

## Operator action required
1. Review the gate-and-continue vs break-on-death choice.
2. Deploy app.py with the `Operator-Signoff` trailer.
3. `incomplete_challenger_dead` is a new status bucket — note it alongside `incomplete_model_dead` / `stopped` / `incomplete_no_close` / `incomplete_terminated` for any status-aware reporting.

No deploy performed. No farm session run.
