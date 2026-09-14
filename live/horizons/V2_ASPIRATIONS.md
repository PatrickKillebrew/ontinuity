# ONTINUITY — V2 ASPIRATIONS (captured for future development, not v1 scope)
*Operator's forward-looking design intent, captured 2026-09-13 so it is not lost. These are DELIBERATELY
DEFERRED past v1 (v1 = the packaged per-operator instance with per-project memory + the design front door).
Documented here per operator: "Document these future aspirations in a way that they don't get lost. Then
we'll get back to what we were already doing." Each is grounded in the discussion that produced it.*

## THE FRAME THAT ORGANIZES ALL OF V2 (settled this session)
Ontinuity has TWO front doors + ONE cross-cutting capability (NOT three front doors):
- INTAKE door: an outside person with a problem fills a questionnaire → a structured matter.
- DESIGN/BUILD door: the operator works a matter in the chat window (like this conversation) → accumulating
  knowledge with memory continuity. This is ~90% of a user's day and is v1's core.
- VERIFICATION (the adversarial engine): NOT a third door — a GATE a session ROUTES A SPECIFIC LOAD-BEARING
  OUTPUT THROUGH when fabrication-freeness matters, then returns the certified artifact into the design
  conversation. Watched (optionally) through the Governor cockpit. "Verification is a gate the design session
  calls, not a front door." (Operator confirmed.)
WHEN TO INVOKE THE ADVERSARIAL GATE (the resolved answer): route an output through it when a fabricated claim
in it would cause real harm downstream — software to build, a floor-level/safety-critical procedure, a client
deliverable, a compliance number. Leave drafts/brainstorms/outlines/lists in the design conversation (no gate).
The EXECUTION LOG is the mechanism: it makes "I ran/tested/measured/verified X" un-fakeable — so the gate is
most valuable exactly where the deliverable contains claims of that form. It is a FABRICATION TRIPWIRE (the
operator's original intent — "the adversarial review was meant to be exactly that trip wire").

## V2-A — USER-UPLOADED REFERENCE LIBRARIES (the grounding substrate the gate polls)
THE PROBLEM IT SOLVES: today the adversarial gate verifies INTERNAL consistency (execution log + frozen
contract). To verify a claim against EXTERNAL ground truth (e.g. "OSHA 1910.269(l) requires X"), the gate needs
an authoritative corpus to poll. AIP gets this from a pre-built Ontology; Ontinuity's answer is lighter and
bottom-up: the USER UPLOADS their own ground truth (operator's idea: "make that something the user can upload
themselves — keeps us from having to predict/preload what a user might want").
MECHANISM (additive, reuses the corpus you already have): an uploaded reference library = ANOTHER corpus, but
SHARED/READ-ONLY reference (vs a matter's accumulating isolated corpus). The existing VERIFY_CITATION gate
polls it — a claim gets grounded in, or flagged against, the library. This is the two-tier retrieval already
designed: FACTS isolated per matter; shared REFERENCE (the library) readable across matters (the same
methodology-vs-facts split as the four-stage pipeline's two-axis isolation rule).
WHY IT MATTERS (the gravity): a generic AI drafting a safety procedure reasons from (possibly stale/wrong/
hallucinated) training data. Ontinuity drafting one VERIFIED AGAINST A CITED library produces something
AUDITABLE AND DEFENSIBLE — every safety-critical step cites the regulation it rests on. For a compliance-driven
role, defensible-and-cited IS the job.

## V2-B — AUTO-FETCH FROM AUTHORITATIVE SOURCES (the compounding "magic" version)
Given a matter's topic ("confined-space entry training at Plant 34"), the system FETCHES the exact relevant
public regulations itself (OSHA 1910.146 via eCFR API / OSHA's public standards — public + structured +
retrievable) and populates a reference library automatically, then DRAWS THE TRAINING CONTENT *FROM* the actual
regulation with citations back to the source. Operator: "trainings could be drawn from the exact regulations
that Cornel needs to train people about." This is the killer version — not "AI wrote a training" but "AI built a
training grounded in and citing the live federal regulation, verified before it shipped."
BUILD PATH (clean, additive, no new architecture): (1) upload a reference library → shared read-only corpus;
(2) VERIFY_CITATION gate polls it; (3) later: auto-fetch relevant public regs into a library by matter topic;
(4) generate content FROM the library with source citations. SEQUENCING: user-upload ships first (simplest, no
external deps, ~80% the existing corpus mechanism); auto-fetch is the v2 magic on top.

## V2-C — INTAKE AS A FRONT DOOR FOR MATTERS (closing the loop between the doors)
Operator's "thinking out loud": an employee/manager fills out an intake for an incident/compliance item, and it
BECOMES A MATTER in the operator's punch list. Incidents and compliance updates enter through the INTAKE door
(structured, filled by whoever holds the info), land as MATTERS the operator (e.g. Cornel) then works through
the design door with full memory + verification. This unifies the architecture: INTAKE creates matters →
DESIGN works them → VERIFICATION grounds their load-bearing outputs against reference libraries. Incident
reports / compliance records created or updated through the intake door, surfaced to the operator via the punch
list. (Grounded in: the existing intake pipeline + seed_tenant/new_project + the punch-list mechanism — the
pieces exist; wiring them into this flow is the v2 work.)

## V2-D — ADVERSARIAL SESSION UI / GOVERNOR AS THE WATCH-WINDOW
The design door is the chat window. The adversarial engine needs no separate front-door UI — it needs a TRIGGER
from within a session ("verify this before it ships") and a PLACE TO WATCH it run: the Governor cockpit
(observability into the gates firing). A NAMING MODAL for a new matter belongs at the DESIGN door (a memory
concern — the user names their own matter, with a confirm modal), NOT at the adversarial layer (which inherits
the matter scope from whatever invoked it). (Operator's modal idea, placed correctly: naming = design/memory;
the adversarial gate doesn't create projects, it verifies outputs within one.)

## THE MARKET THESIS (why this is worth building — operator's conviction + the analysis)
Ontinuity's differentiator vs generic AI memory: it stores what was DONE, CHALLENGED, and GROUNDED — with
enough cross-referenced provenance that the record is AUDITABLE and SELF-CORRECTING, not just retrievable (a
stored fact can be wrong; a reconstructable, verified record lets you CATCH the wrong fact — demonstrated live
this session when the corpus reconstructed that a manual claim about seed_tenant was false). vs Palantir AIP:
AIP grounds against a pre-engineered Ontology (enterprise-scale, data-engineering prerequisite); Ontinuity
grounds against an accumulating adversarial-verified RECORD + user-brought reference libraries (useful from the
first session, models nothing up front, no data-engineering prerequisite). Different market: bottom-up,
single-operator, compliance-driven. THE COMPLIANCE ANGLE is the wedge (operator: "the impact on the compliance
world could be game changing"): a fleet safety manager's job IS liability + defensibility across many sites;
"here's the training/procedure, verified fabrication-free, with the OSHA citation for every safety-critical
step" is not a nice-to-have — it is the whole value. The flywheel: each verified matter's established results
become reference for the next (Plant 51 starts from Plant 34's verified template + the same reg library), so
the knowledge base AND the reference libraries compound over time.
