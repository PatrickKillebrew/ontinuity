# FOUNDATION SPEC — Coordinator/Worker Multi-Seat Architecture
*Operator concept, June 8. Foundation captured now; build is post-hardening. The control-conversation-as-UI + Governor pattern is already proven; this is its disciplined generalization to N parallel seats.*

## Shape (standard orchestrator-worker, mapped onto what already exists)
- **MASTER seat (coordinator/adjudicator):** owns the punch list, breaks it into work blocks chunked by problem class, dispatches ONE self-contained block at a time to a worker. Workers never see the punch list — only their block. The master absorbs worker outputs as INPUTS to its next-step decision and picks the next block.
- **WORKER seats (sub-seats):** each gets a block, grinds to truth in its own ephemeral working space (its own lineage-sealed engine instance + mailbox), appends ONLY settled, relevant results to the shared corpus, signals done, gets the next block. Possible lineages: Claude, GPT (paid account), Gemini — seat protocol is agent-agnostic; HARNESS:MODEL records who actually sat there.
- **CORPUS:** one shared durable store. Workers draw ephemeral working data; commit only settled results. Append-mostly, receipted — concurrent session writes are the designed behavior (main+farm already do this).
- **CONTROL CONVERSATION + GOVERNOR:** the human's single pane of glass over all N instances. Governor already shows main+farm; extends to farm-2, farm-3.

## Collision avoidance (the burn-in solution, generalized)
Collisions are avoided the same way the burn-in avoided colliding with main: SEPARATE SYSTEM INSTANCES, SEPARATE MAILBOXES. Each seat drives its OWN engine instance (its own Railway service), lineage-sealed like the farm, pointed at the shared corpus. N workers = N instances = N mailboxes = 1 corpus. No shared live engine to race on.
The one remaining shared-write hazard is the queue (agent_queue.md, last-write-wins). DISCIPLINE: each seat amends its own queue section, OR queue writes are append-only and non-overlapping. This is the only coordination structure that must exist before turning multiple seats loose.

## CORE GUARDRAIL #1 — coordinator does NOT become an unchecked judge
The master COORDINATES; it does not unilaterally judge worker output quality. Its "next-step decision" is gated by the SAME deterministic loop discipline the single seat already uses: the master proposes the next move and the system must AGREE before proceeding — exactly as the current seat picks its next punch-list item and the loop agrees. No single model's judgment is the decision, at the orchestration layer just as at the session layer. Punch-list amendments are ratified (by the loop or the operator), not asserted by the master alone. This keeps the thing that makes Ontinuity Ontinuity intact one level up.

## CORE GUARDRAIL #2 — coordination escalation inherits autonomous-modal handling
When the master hits a coordination point that would normally escalate to a human (loop doesn't agree, worker stalls, ambiguous next step), it gets a BOUNDED AUTONOMOUS WINDOW to self-resolve — the exact pattern shipped June 8 for session modals (MODAL_TIMEOUT_AUTONOMOUS_S = 90s + auto-clear). It escalates to the human operator ONLY if it genuinely cannot resolve within the window. This is what makes the master/worker loop unattended instead of constantly pinging the operator — the same fix that finally made the burn-in run unattended, applied at the orchestration layer. The coordinator inherits the autonomy fix; it does not invent new control logic.

## Two modes (disjoint vs overlapping)
- DISJOINT (parallel bug discovery — the near-term value): workers get resource-disjoint blocks, ~N× throughput on the punch list for the cost of accounts already paid for.
- OVERLAPPING (divergence-as-truth-signal — the deep value): point two DIFFERENT-lineage workers at the SAME problem; disagreement is data. Two lineages rarely fabricate the same thing, so cross-lineage agreement is a strong truth signal. (Ties to the parallel-Researchers horizon item.)

## Sequencing
Foundation captured now. Build is post-hardening / post-tenancy. Provisioning a worker = "stand up a lineage-sealed engine instance + mailbox pointed at the corpus" — document that as a checklist so seat #3 is a checklist not a discovery. Open test: how a free-tier frontier account handles sustained seat work (rate limits, timeouts). The control-conversation + Governor single-pane pattern is already proven; this spec is the disciplined path to lighting up additional seats without undoing the architecture's core invariants.
