# SPEC — Four-Stage Refinement Pipeline (intake → solution proposal)

Status: DEFINED (design, partially proven). Stage 1 (intake) is LIVE. Stages 2–4 are DESIGN. First real run-through: Katie / Senior Home Services (see live/integrations/senior-care/FOLD.md). Folded to corpus 2026-06-14.

## What this is
The pipeline that turns a client's raw intake into a grounded solution proposal. It is the core Ontinuity offering made concrete: not "the model gives a confident answer," but "a staged, adversarially-checked process produces a proposal where you know what is verified, what is assumed, and what is still open." The session deliverable is NOT the solution — it is the SPEC the build runs on.

## The four stages
Each stage is a Tetraform session. Each writes provenance-tagged output to a per-project mini-corpus. The final stage composes from the whole chain — depth comes from the ASK and the staging, not from the intake alone.

1. INTAKE — capture the client's situation in their own words. (LIVE: intake.html / prompts/intake_system.txt.)
2. PROBLEM-DEFINITION — produce the problem set and the flagged unknowns. NO solutions yet. Surfaces what seed material / information the later stages will require. Its most valuable output is often the LIST OF WHAT TO LEARN.
3. DECOMPOSITION — break the defined problem into buildable pieces plus a build order.
4. SOLUTION PROPOSAL — compose the proposal from the entire chain (intake + problem set + decomposition), tagged by provenance.

## Provenance tags (the load-bearing discipline)
Every finding in the mini-corpus, and every claim in the final proposal, carries a status:
- confirmed — established from the client's own intake or a verified source.
- assumed — a working assumption, labeled as such, not laundered into fact.
- open — an unresolved unknown the proposal explicitly flags (e.g. a question only the client or a third party can answer).

This is what keeps the pipeline from laundering guesses into confident proposals. The proposal SHOWS its provenance to the client — verified vs assumed vs open becomes a client-facing feature, the trust spine made legible. (Proven in the Katie proposal: problem = confirmed from intake; insight layer = later benefit; ClearCare access = open, pending their answer.)

## Mini-corpus = the handoff mechanism
Each stage writes status-tagged output to a per-project mini-corpus (reuses the project-isolation work — scoped per project, no cross-project data bleed). The next stage PULLS from the corpus (durable, query-based) rather than receiving a fragile pushed injection. The final stage knows truth from assumption from open-question because the corpus carries the tags.

## Two-axis isolation rule (permanent)
1. FACTS about a project come ONLY from that project's own mini-corpus — strict, every stage.
2. METHODOLOGY / build-patterns MAY be read from the main corpus, but ONLY in the solution-half stages (3 decompose, 4 propose), read-only, never written back. Main corpus is write-sealed against every client session, always. Stages 1–2 (problem-understanding) stay STRICT — no methodology read.
Rationale: the bleed risk is DATA bleed (one client's facts leaking into another's). Methodology read is safe — reusable craft (the HOW) is not project facts (the WHAT). BUILD ORDER: strict-isolation-everywhere first, THEN cut the methodology-read window into stages 3–4 as a deliberate second layer.

## Second-loop / convergence (the strong version)
Re-run the loop only with NEW information (resolved unknowns from the prior pass's open-list) — not the same inputs again (that weak version is a trap; don't build it). The mini-corpus makes re-runs incremental: patch the changed rows, re-run only the dependent stages. STOP when the remaining `open` rows no longer change the proposal — a convergence criterion, not a loop count. The first pass's most valuable output is the list of what to learn; the second pass consumes that list.

## Output: the solution proposal
The composed proposal is the pipeline's product. Register: plain-language, professional, minimal verbosity, structured as the stages (problem-as-defined → decomposed → composed → how it fits → path to delivery → what we need from the client). Investment/price is handled by the operator directly, NOT baked into the generated proposal. Branding: gold nested-hexagon mark (two concentric hexagons + center dot) inline with the wordmark, vertically centered; warm gold #c9a84c is the index.html brand value but it is tuned for the site's DARK background — on a WHITE-page document warm it toward ~#B57E2E (honey-amber) so it reads handcrafted, not cool/flat. Provenance DISCIPLINE always governs the build; provenance DISPLAY (visible confirmed/assumed/open tags vs. softened prose) is a per-client tone choice — for a first emotional delivery, soften to warm prose with one gentle "to confirm" touch (proven: Seniors Helping Seniors, 2026-06-14).

## Relation to the rest of Ontinuity
This pipeline is the front half (problem → spec). The propose→worker-build→peer-review→deploy gate is the back half (spec → built, verified software). The self-healing drift-repair keeps the delivered tool alive. Together: intake to a living, maintained product, with the trust spine upstream in build/verify, not in the shipped runtime.
