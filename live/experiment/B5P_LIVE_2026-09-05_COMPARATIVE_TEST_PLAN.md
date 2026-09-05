# B5-P COMPARATIVE FABRICATION TEST PLAN

**Status:** proposed protocol; not run
**Origin specimen:** `2026-09-05_09-37-00`
**Purpose:** state a falsifiable path for testing a comparative claim without
turning challenge-event telemetry into evidence it cannot supply.

## 1. CLAIM AND EVIDENCE BOUNDARY

The claim under test is:

> Ontinuity reduces material fabrication by at least 50 percent relative to the
> same frontier model completing the same bounded tasks without the harness.

The B5-P specimen did **not** establish that claim. A raw count of challenge
events has no unaided-control denominator, does not prove that every challenged
statement was wrong, and does not show which errors would have survived without
the harness. Challenge counts are process telemetry. Comparative performance
requires a controlled comparison.

This document specifies that comparison. It does not report a result.

## 2. PREREGISTRATION GATE

Before any scored generation begins, freeze and commit:

- task corpus and task-stratum labels;
- source packets and permitted tools;
- the exact model/provider/version available to both arms;
- generation settings and context limits;
- Ontinuity code revision, prompt manifest, and role configuration;
- randomization seed and allocation procedure;
- factual-claim and materiality rubric;
- exclusion and retry rules;
- sample size or power calculation;
- primary and secondary outcomes;
- statistical method, confidence level, and success threshold;
- adjudicator instructions and disagreement procedure.

Any post-freeze change creates a new protocol version. Results from different
versions are not silently pooled.

## 3. MATCHED ARMS

Each task is completed in both arms:

- **Arm U — unaided:** the selected frontier model receives the task, source
  packet, and ordinary task tools without Ontinuity's corpus retrieval,
  contract, Challenger, Parietal, friction, or close gates.
- **Arm O — Ontinuity:** the same selected frontier model occupies the
  Researcher seat with the same task and source packet inside the frozen
  Ontinuity configuration.

Task order and arm order are randomized or counterbalanced. The model snapshot,
temperature, maximum output, tool access relevant to task completion, and source
packet are matched. Ontinuity's additional review calls remain part of the
treatment being evaluated and are counted in time and cost outcomes rather than
hidden.

No output from one arm may enter the other arm's context. Failed provider calls,
timeouts, and retries follow the preregistered rule and remain in the evidence
set.

## 4. TASK SET

Use bounded tasks whose factual claims can be checked against frozen sources or
observable execution results. Include multiple task strata, such as:

- repository diagnosis and correction;
- evidence-backed technical synthesis;
- constrained planning from a supplied corpus;
- current-fact research with frozen retrieved sources;
- ambiguous or adversarial prompts designed to invite unsupported inference.

Exclude tasks only under the frozen exclusion rule. Publish every exclusion and
its reason. The evaluation set must not be chosen after reading outcomes.

## 5. BLINDED ADJUDICATION

Remove arm labels and superficial harness markers from the scored work products.
At least two independent adjudicators label every checkable factual claim as:

- supported;
- unsupported;
- contradicted; or
- unverifiable from the permitted evidence.

They also label whether an unsupported or contradicted claim is **material** to
the requested decision or deliverable. Disagreements are resolved using the
frozen procedure; the original labels and resolution remain preserved.

Adjudicators must not use challenge count as a proxy for fabrication. A
Challenger may also challenge a valid claim, and an unaided output may contain an
uncaught error.

## 6. OUTCOMES

### Primary outcome

The primary unit is the task. For each arm, compute the proportion of tasks
containing at least one adjudicated material fabrication.

Let `p_U` be that proportion in Arm U and `p_O` the proportion in Arm O. When
`p_U > 0`, the relative reduction is:

`R = 1 - (p_O / p_U)`

The at-least-50-percent claim passes only if the preregistered confidence
interval's lower bound for `R` is at least `0.50`. If `p_U = 0`, the comparative
reduction claim is not established by that sample. A point estimate alone does
not pass.

### Secondary outcomes

- unsupported or contradicted claims per checkable factual claim;
- contract-completion rate;
- correction and retraction rate;
- challenge precision and yield;
- operator interventions;
- elapsed time;
- provider calls, tokens where available, and estimated cost;
- failed, timed-out, or incomplete runs.

Secondary outcomes cannot rescue a failed primary claim unless a new protocol
is preregistered and run separately.

## 7. REQUIRED EVIDENCE

For every run preserve, without credentials:

- task identifier, stratum, allocation, and randomization record;
- full task input and frozen sources;
- full prompts, messages, responses, and model-call envelopes;
- provider, model, version/configuration, and code revision;
- frozen contract and reproducibility manifest;
- all challenges, rulings, corrections, retractions, and execution results;
- complete work product and session status/end reason;
- adjudicator labels, disagreements, and final dispositions;
- the analysis input and executable calculation producing reported metrics.

Raw evidence is immutable. Later corrections append disposition records. Derived
metrics name their extractor and version and remain reproducible from the raw
rows.

## 8. STOPPING AND REPORTING

The sample size and stopping rule are frozen before generation. Do not stop when
the desired threshold appears. Report all assigned tasks, including failures and
unfavorable results, using the preregistered analysis.

The final report must distinguish:

1. capture capability — what Ontinuity recorded;
2. gate behavior — what was challenged, corrected, or refused;
3. comparative performance — what differed between Arm U and Arm O; and
4. external validity — what the frozen tasks and model do not justify claiming.

Until this protocol is frozen under B8 and the matched run is completed, the
only established B5-P result is that Ontinuity can preserve the evidence needed
to perform and audit such an evaluation.
