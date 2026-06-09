# Design Spec — Governor Punch-List Panel

**Status: DESIGN ONLY. No build, no deploy. Read-only, auth-gated, fits the existing Governor. Renders the restructured punch list (live/PUNCH_LIST.md).**

## Purpose
The operator's stated problem: "I can't see the punch list, I rely on faith." The queue is current but is a 240-line append-only log with no resolved state. `live/PUNCH_LIST.md` now distills it into DONE / IN-PROGRESS / OPEN. This panel renders that resolved view in the Governor so "what's done, what's in flight, what's next" is legible at a glance — past, present, future — without reading the archive by hand.

This panel is the **legibility** half; the Adjudicator panel (spec 65214f3a) is the **action** half. This one shows the whole resolved state read-only; the Adjudicator records sign-off on the actionable subset. They are complementary and cross-link (see Overlap).

## Fits the existing Governor
Same as the live monitor (`live/governor/governor.html`): X-API-Key session gate, `/governor/data`-style fetch, dark panel aesthetic, same `$()`/loop render pattern. Read-only — no write, no actions on this panel.

## Data source — the structured punch list
A new read route `/governor/punchlist` (auth_required, GET) returns the parsed punch list as JSON. It fetches `live/PUNCH_LIST.md` (VPS-local mirror preferred to avoid shared-egress GitHub rate limits; GitHub API fallback) and parses it server-side into:
```json
{
  "resolved_at": "2026-06-09",
  "done":        [{ "title": "...", "closed_by": "5dbc9caa | receipt #214 | deploy 34" }],
  "in_progress": [{ "title": "...", "tier": "REVIEW", "risk_tier": "REVIEW", "awaiting": "operator sign-off deploy", "ref": "69fdb49b" }],
  "open":        [{ "title": "...", "tier": "HIGH", "cluster": "product-blocker" }],
  "counts":      { "done": 22, "in_progress": 9, "open_high": 4, "open_med": 11, "open_minor": 7 }
}
```

### Format contract (keeps the file dual-use)
The file is both human-readable and machine-parseable; the panel depends on a light, stable format the distiller maintains:
- Section headers exactly `## DONE`, `## IN-PROGRESS`, `## OPEN`, with OPEN sub-headers `### HIGH|MED|MINOR|OPERATOR-GATED`.
- Each item is a `- **Title**` bullet; DONE items name a closing ref (sha / `receipt #N` / `deploy N`) in the bullet; IN-PROGRESS items carry a `[TIER]` bracket tag and an "awaiting …" clause.
- The parser is tolerant: anything it cannot classify falls into the section it sits under with `tier: null` (never drops an item). **Open question P1**: keep the parser tolerant against a prose file, or have the distiller also emit a sidecar `PUNCH_LIST.json` so the panel reads structured data directly and the .md stays purely human? (Recommend the sidecar once the format settles — removes parser fragility; until then, tolerant parse.)

## UI — three columns, past/present/future
One panel, `Punch List`, with a summary strip and three columns (stacks vertically on phone, the operator's primary device):
- **Present (IN-PROGRESS)** — leftmost/top, the operator's live attention. Each item: title, tier badge, and the "awaiting" state (sign-off deploy / VPS build / design). Items awaiting sign-off **link to the Adjudicator panel** for the action.
- **Future (OPEN)** — grouped HIGH / MED / MINOR / operator-gated, collapsible per group; HIGH expanded by default. The forward queue, prioritized.
- **Past (DONE)** — collapsed by default, chronological when expanded, each line citing its closing ref. The "it actually happened, here's the proof" column — directly answers the faith problem.
- **Summary strip**: counts (done / in-progress / open-by-tier) so the shape is one glance.

Color: reuse the Outcome-Ledger palette — DONE green, IN-PROGRESS amber, OPEN neutral, HIGH-tier accented. Tier badges match the Adjudicator's SAFE/REVIEW/RISK colors so the two panels read as one system.

## Overlap with the Adjudicator panel (deliberate, cross-linked)
IN-PROGRESS items awaiting sign-off deploy appear in **both** panels: here as legibility ("Fix #4 committed, awaiting deploy"), there as an actionable sign-off row. The punch-list panel **links** such items to their Adjudicator row rather than duplicating the action. Rule: legibility lives here, action lives in the Adjudicator, one source file (PUNCH_LIST.md) feeds the state, the provenance ledger feeds "is it signed yet."

## Refresh
Punch-list state changes on the order of commits, not seconds — poll on panel open + a manual refresh + a slow interval (e.g. 60s), not the monitor's fast loop. The file's `resolved_at` is shown so staleness is visible (and is itself a nudge to re-distill).

## Open questions for operator
- **P1** (above): tolerant markdown parse now vs. a `PUNCH_LIST.json` sidecar once the format settles. (Recommend sidecar later.)
- **P2**: who re-distills PUNCH_LIST.md, and when — manually each session, or a distillation step folded into the close ritual so the resolved view never lapses the way conversation logging did? (Recommend: fold re-distillation into the same ritual as the conversation record + ledger, so all three stay in sync — see the convergence note.)
- **P3**: should DONE be capped/paginated (it only grows), e.g. show last 20 + "older" expander reading the archive queue? (Recommend a cap with an archive link.)
