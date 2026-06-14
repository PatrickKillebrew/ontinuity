# INTEGRATION FOLD — Senior Home Services (Katie's project)
First Ontinuity-built external product. Also the TEMPLATE for the future-integrations rhythm: each integration gets its own fold here under live/integrations/<name>/. This is the append-and-refine record (plant ideas, bank them half-framed, sharpen over time) — the same rhythm that built Ontinuity.

Status: DESIGN / pre-build. No code yet. Katie's intake is the one real data point. Started 2026-06-13.

---

## WHAT IT IS (scoping rubric — carved 2026-06-13)
The product is CODE — a per-account, isolated, snapshot-holding, SMS-native emergency-coverage matcher that resolves availability BY ASKING, NOT STORING. The never-delete corpus accumulates silently from day one as exhaust. The AI is UPSTREAM in the factory (the Ontinuity worker pipeline builds it; drift-repair keeps it alive against ClearCare changes) and LATER in the insight layer (year-two, mining the accumulated corpus for patterns no competitor keeps the data to see). The customer installs something as simple as a browser add-on and never sees the machine behind it.

DESIGN LAW: code first; sprinkle AI ONLY where code can't satisfy the fix. Minimum AI at runtime is what makes it reliable enough to charge for. AI lives in BUILDING and HEALING the tool, never in the live coverage decision (human-in-the-loop on the actual call). "Boring reliable tool, intelligent factory behind it."

## THE PROBLEM (from Katie's intake)
A caregiver can't make a shift; the owner scrambles to find coverage for a vulnerable elderly client. Costs Katie ~$140/week (~$600/month) in lost time/money. The tool "lives to meet the occasion" — event-triggered, near-zero cost between emergencies.

## CORE DESIGN — two grounded layers, both code
1. FOUNDATION SNAPSHOT (availability base layer): scheduled availability-poll texts at known times each day. Reply within a ~20-min window = available; SILENCE = definitively unavailable (sick / with a client / off / unwilling — reason irrelevant). KEY INSIGHT: the known-time convention turns a non-reply into SIGNAL, not missing data — evidence-of-absence discipline applied. The labor pool maintains the dataset itself, at near-zero cost, with no stored-flag staleness. Caregivers can also: cancel a regular shift at a preset days-in-advance rule (advance warning), self-mark available to pick up, or poll-text the community when a shift opens.
2. RUNNING SNAPSHOT (emergency matcher): sits ON TOP of the foundation layer. On the trigger event (caregiver out), filter ClearCare schedule for not-booked candidates (code), rank by stored preferences (code), text top N "shift open, reply YES to claim" — availability resolves by who replies (query reality at moment of need, don't hold perfect state). The human owner makes the actual coverage decision.

WHY NO AI NEEDED for availability/matching: schedule-filter (code) -> confirmation-loop text (code) -> preference-ranking (code). It's search-and-notify, not inference. SMS-native because a stressed coordinator at 6am wants to text, not log into a dashboard (the OpenClaw interface-reach lesson).

## DATA ACCESS (the load-bearing unknown — recon, not yet resolved)
ClearCare/WellSky HAS access surfaces (correcting the earlier "no API" assumption): Connect API (FHIR-compliant REST, base https://connect.clearcareonline.com/v1/, /practitioners/ + /appointment/, GET/POST/PUT/DELETE, JSON — exactly caregiver+scheduling data) under the ClearCare Connect API Agreement; plus an Insights Agreement offering Third-Party API and JDBC (direct DB read) modes.
HARD CONSTRAINT: both agreements forbid reverse-engineering / decompiling / derivative works / unauthorized scraping. WellSky is HITRUST-certified, HIPAA data. So the "cooperative layer from outside" must use the SANCTIONED surface (like building on Claude Code's CLI/MCP, NOT decompiling its binary). Forbidden path = scrape/reverse-engineer the web UI. Sanctioned path = build against Connect API / Insights / JDBC as a licensed "Application," Katie's agency the licensed party.
OPEN: will WellSky license a SMALL SINGLE agency onto Connect/Insights, at what cost/friction? Docs suggest the API is mostly used by big referral networks, not solo agencies. FIRST MOVE = a phone call (procurement/licensing question, sharpened): "which mode applies to a single agency wanting programmatic access to its OWN data, what's the path/cost, what counts as an approved Application?" support@clearcareonline.com.
FLOOR FALLBACK (always works, fully sanctioned, no API license): Katie exports her OWN data from the ClearCare UI (reports/CSV) -> tool ingests -> adds capability. Many integrations start here (manual export -> process -> value) and graduate to API once value justifies licensing cost.
GENERALIZATION (the product seed): build against the STANDARD (FHIR), not the vendor. A FHIR helper layer happens to work with ClearCare AND any FHIR-compliant health system. Don't build a ClearCare integration — build a vendor-agnostic home-health helper layer that works with ClearCare first. (WellSky also uses Open Referral HSDS for its Community Services API — standards-friendly.)

## SELF-HEALING SUPPORT (reuses Ontinuity machinery that already exists)
The corpus self-healing parts map ~1:1 onto ClearCare-update support:
- drift-check (live/specs/deploy_drift_check.md): the WATCHER. Repointed from "deployed binary vs repo HEAD" to "ClearCare API shape vs our integration's expected shape." A ClearCare update = a drift event. Reads both sides fresh at comparison time (the lesson already learned).
- shepherd (live/shepherd.py): the orchestration loop — start/answer/watch/verify/pace/next, STOPS on modal / repeated failure / missing receipt. Self-healing controller that knows when to proceed autonomously vs escalate to a human.
- propose -> worker-build -> peer-review -> deploy gate: PROVEN end-to-end 2026-06-13 (worker4 signed off an outage-fix, deployed clean). The "build, check, deploy in real time" is demonstrated, not hypothetical.
FLOW: ClearCare update lands -> drift-watcher detects shape mismatch -> block into worker pool -> worker builds adapter fix -> second worker peer-reviews -> control deploys -> customer never files a ticket because it self-repaired first.
SHARP LINE (keeps the knife from slipping): self-heal only the KNOWN, BOUNDED failure class (vendor API shape drift — deterministic "is it broken," mechanical fix). Open-ended/judgment support stays HUMAN/billable. Drift-repair is on the right side of the line; anything needing judgment is not.
ECONOMIC POINT: automation collapsing the common support class (drift) is what makes the recurring subscription lucrative vs billable-hours. Two-tier support: automated drift-repair (common) + billable-hour calls & self-help guide (genuinely novel/rare).

## PRICING (frame set, number NOT locked — needs more real intakes)
Value anchor: ~$600/month of pain (Katie). Operator instinct: $60-80/month introductory (capture ~10-13%, customer keeps ~87-90%, obvious ROI). Sharpening pushback banked: $60-80 may be the FLOOR — too-thin margin gets eaten by support cost, and too-cheap can read as not-serious for an operational lifeline; band of $79-129+ still leaves the customer most of the value. DON'T LOCK until 2-3 more owner cost-of-problem intakes + one real second-install (delivery cost). Price = measured value / deliverability, landing where ROI is a no-brainer. Introductory framing leaves room to raise without it being a "hike."

## MARKET
Beachhead = ~4,000 agencies on ClearCare/WellSky personal-care software (the ones with Katie's exact problem on Katie's exact platform). Broader = 15,000+ US non-medical home care agencies (reachable later via the FHIR-generic layer). Tailwind: ~61M Americans 65+; 64% of agencies see auto-scheduling/shift-matching as AI's biggest industry impact (demand-side already primed). First customers = the SHS owners Katie tells about her solution (word-of-mouth referral, the natural sales motion).

## INSIGHT LAYER (year-two expansion — the original slice nothing in the market reveals)
Never-delete corpus per account = a longitudinal record competitors don't keep (they overwrite). Over a year, each agency's corpus could surface what an owner FEELS but can't SEE: structural weak-point shifts (e.g. Tuesday evenings), load-bearing caregivers who cover most emergencies (protect them), early-warning of a quit (declining response rate). This is the Ontinuity insight layer applied; ADVISORY to the owner, never autonomous. Worthless day one (no history); switches on once data accumulates. Data collection is free exhaust of operating, so the year-two raw material banks from day one at no extra cost. Also a RETENTION MOAT: the accumulated corpus is switching-cost.

## OPEN THREADS / NEXT MOVES (plant-and-bank)
- Recon call to WellSky/ClearCare: which access mode for a single agency, cost, approval friction, "approved Application" definition.
- Run cost-of-problem intake on 2-3 of Katie's referral owners (turns pricing from guess to calculation).
- Decide path: live Connect/Insights API sync vs export-ingest floor (depends on the recon call).
- Build-vs-buy the SMS layer (cloud box / always-on; situational-awareness polled periodically).
- Per-account isolation = reuse today's Ontinuity project-isolation work (scoped per-account corpus, no cross-account data bleed — HIPAA-adjacent requirement, already solved structurally).
- Year-two insight layer: bank, don't build (no data yet).

## WHAT THIS MEANS FOR ONTINUITY ITSELF
This is the first product off the Ontinuity factory line, and it sharpens what Ontinuity IS: the intelligent factory that builds + heals boring-reliable tools, with the trust spine living upstream in build/verify, not in the shipped runtime. Senior-care is the legibility artifact — a real deployment on a real business that answers the "works on a toy, not my real problem" objection with evidence. The forward-deployed-engineer profile (decompose a messy real problem, orchestrate the build, verify, own the result) demonstrated on a live case.
