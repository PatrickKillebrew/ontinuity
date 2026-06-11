# DECISION MEMO — Established Results Ledger (ERL) enablement

*Status: PROPOSE-ONLY (no build). Authored by worker1 (claude:opus-4.8) under block ERL-1, dispatched by control. Grounded in the live corpus (established_results schema + 0-row count), the live app.py read from the repo, and the Projenius system prompt's SYNTHESIZE format. Inferences labeled.*

## THE DIAGNOSIS (confirmed from code + corpus, not recalled)
established_results has 0 rows across all sessions. The table is well-formed (result_id, result_text verbatim, confidence ESTABLISHED/PROVISIONAL/RETRACTED, supporting_sessions JSON, confirmation_count, retraction fields, established_at). It is empty for two independent reasons, BOTH of which must be fixed for structured persistence to work:

1. WRITER UNCONFIGURED. call_projenius (app.py ~979) gates on `has_projenius = bool(projenius_cfg.get("api_key") and projenius_cfg.get("url"))`. The live engine's projenius config is empty (url/api_key/model all ""), and the PROJENIUS_* env vars are not set, so has_projenius is False and call_projenius returns early. SYNTHESIZE therefore never runs. run_projenius_synthesize IS wired into the end sequence (app.py ~3027, in a 30s daemon thread) — it just no-ops because the provider is absent.

2. NO PERSIST PATH. Even if Projenius were configured, its SYNTHESIZE output is never parsed or inserted. There are ZERO references to established_results anywhere in app.py (confirmed by grep on the live source) — no INSERT, no parser. At app.py ~3034 the SYNTHESIZE return value only drives a socket emit "Established Results Ledger updated." That message is a silent-success illusion: it fires on a non-empty text return while nothing reaches the table. (INFERENCE, labeled: this misleading emit is itself worth fixing regardless of the decision below, so the UI stops claiming a write that never happens.)

3. THE FOLDS ALREADY FUNCTION AS A WORKING ERL BY HAND. The agent_queue.md folds + PUNCH_LIST.md carry what is established, retracted, and open, keyed on shas/receipts, and are the artifact seats actually orient from today. The ERL's job is already being done — manually, in prose, by the close ritual — just not in the structured table.

## THE PROJENIUS SYNTHESIZE FORMAT (already specified, ready to parse)
The Projenius prompt already defines an exact, parseable per-entry format for SYNTHESIZE:
```
RESULT: [verbatim, complete, not paraphrased]
SESSION: [session ID]
BRANCH: [branch name]
CONFIDENCE: [ESTABLISHED / PROVISIONAL]
NOTES: [one sentence, or omit]
```
and a retraction variant (same RESULT text, CONFIDENCE: RETRACTED, RETRACTED_BY, GROUNDS). These fields map 1:1 onto the established_results columns. So the parser is small and deterministic — the format is not the hard part.

## OPTION A — WIRE STRUCTURED PERSISTENCE
Make the table the source of truth. Four pieces, in order:
1. Point Projenius at a working provider (PROJENIUS_URL / PROJENIUS_MODEL / PROJENIUS_KEY env on the engine — same pattern as the other roles; a small model is fine, this is synthesis not generation). OPERATOR action (env + deploy).
2. Splice a SYNTHESIZE-output parser + INSERT at app.py ~3034: parse the RESULT/SESSION/BRANCH/CONFIDENCE/NOTES blocks, upsert into established_results (new rows ESTABLISHED/PROVISIONAL; retractions update the prior row's confidence + retraction fields; confirmation_count++ + append to supporting_sessions when a result recurs). Committable code change (app.py, watched path -> /diag/engine check + operator deploy).
3. One-time fold->ERL backfill: walk the existing agent_queue folds' established/retracted items into established_results so the table starts populated rather than empty-from-now. One-shot script, RISK-light (additive inserts), but it is a JUDGMENT-bearing extraction (deciding what in the prose folds counts as an established result) — so it should be operator-reviewed, not silently bulk-loaded.
4. (Recommended add-on) fix the misleading "ledger updated" emit so it only fires on an actual INSERT count > 0.

WHAT IT BUYS: queryable, structured cross-session truth — confidence levels, confirmation_count across independent sessions, retraction provenance, and the SEARCH/ORIENT Projenius modes can pull exact ledger text instead of re-deriving from folds. It makes "context continuity across branching research over time" (the stated singular value proposition) a queryable property, not a hand-maintained prose artifact. Confirmation_count + supporting_sessions in particular are things prose folds cannot cheaply express.

WHAT IT COSTS: a provider dependency (another configured model + its failure modes + cost), a watched-path app.py change, a parser to maintain against the prompt format (drift risk if the prompt format changes and the parser doesn't — the same currency-discipline burden as the gate constants), and a judgment-bearing backfill. It also introduces a SECOND source of truth (table + folds) that must be kept coherent, or they decohere the way the manual did from the code.

## OPTION B — KEEP IT FOLD-CARRIED
Leave established_results empty (or drop it from the active design) and keep the folds as the ERL. Optionally: document the folds AS the ERL of record, and make the empty table's status explicit so a reader doesn't mistake 0 rows for "nothing established."

WHAT IT BUYS: zero new dependency, zero watched-path change, one source of truth (the folds), and it matches how seats actually work today. The close ritual already maintains it. No parser to keep current, no provider to configure, no backfill judgment call.

WHAT IT COSTS: no structured query — confidence, confirmation_count, retraction provenance stay implicit in prose; the Projenius SEARCH/ORIENT modes can't pull exact ledger rows; cross-session confirmation counting stays manual. The value proposition stays real but stays prose-shaped.

## RECOMMENDATION (worker1, labeled as a recommendation — control owns the call)
Phase it. Do the CHEAP, NON-PROVIDER half of Option A now, defer the provider half:
- NOW (committable, no provider): add the parser + established_results INSERT at the splice point AND fix the misleading emit, but drive it from the EXISTING distillation Delta Log / session_ledger that already feeds run_projenius_synthesize — i.e. make the persist path exist and be correct, gated so it no-ops cleanly when Projenius is unconfigured (exactly as today) rather than emitting a false success. This removes defect #2 (no persist path) without taking on the provider dependency, and turns the current silent-success lie into an honest "ledger not updated (Projenius unconfigured)".
- LATER (operator, when a small synth provider is worth wiring): set PROJENIUS_* env and the table starts filling on every close. Backfill the folds in a reviewed one-shot at that point.
- KEEP the folds as the working ERL throughout. They remain the source of truth until the table has earned trust by running clean for a stretch (mirrors the verification-recipe discipline: prove the write works on real rows before relying on it).

RATIONALE: the two defects are separable. Defect #2 (no persist path + the false "updated" emit) is a correctness bug worth fixing regardless of the strategic choice, and fixing it is committable with no new dependency. Defect #1 (provider) is the part that carries real cost and is reversible/deferrable. Splitting them lets control de-risk: get an honest, correct, gated persist path in first; flip the provider on when the structured ledger's value clearly beats its upkeep. This avoids the worst outcome — a half-wired ledger that SAYS it updated while the table stays empty, which is the current state and is actively misleading.

## WHAT WAS CHECKED (persistence-rule trail)
Corpus: established_results count (0) + full schema. Live app.py (read via raw CDN after the GitHub API rate-limited on the shared egress — the read_repo problem in miniature): call_projenius gating ~979, run_projenius_synthesize ~1005 + its end-sequence call site ~3027/3034, projenius config block (empty), and a grep proving zero established_results references. Projenius prompt: the SYNTHESIZE per-entry format + retraction variant. No build performed; this is propose-only.
