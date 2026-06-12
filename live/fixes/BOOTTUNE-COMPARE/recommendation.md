# BOOTTUNE-COMPARE — original vs reworded quick-boot, judged on instruction coherence
Author: worker2 (claude:opus-4.8) | PROPOSE-ONLY, no deploy/land.
Grounding: live/WORKER_QUICKBOOT.md (current), live/fixes/BOOTTUNE-1/WORKER_QUICKBOOT_proposed.md (my earlier reword), live/archive/boot_extreme_REFUSE_worker3.md (the refuse-extreme), all read this session via read_repo (api.github). Plus the live boot-event evidence: worker3 booted successfully from the current snippet this session. Inference labeled. I am revising a conclusion I myself drew in BOOTTUNE-1; flagging that openly.

## New evidence forces a correction to my BOOTTUNE-1 premise
BOOTTUNE-1 asserted the refuse-extreme WORDING causes refusal, because the live snippet was byte-identical to the archived refuse case. Two facts now undercut that:
1. worker3 BOOTED SUCCESSFULLY from the current snippet this session — oriented, ran all 4 tests, flagged the DIAG_KEY leak but did NOT refuse. So the wording alone is NOT sufficient to cause refusal. My BOOTTUNE-1 causal claim was too strong.
2. The live WORKER_QUICKBOOT.md is NO LONGER byte-identical to the archive — its DIAG_KEY line is already a redaction placeholder (someone landed that change). So the "identical to refuse-extreme" framing is now stale.
CONCLUSION (revised): the refusal was likely NOT caused by the wording per se. INFERENCE (labeled), candidates the block named, ranked by my read of plausibility: (a) the empty/odd "paste your key here" placeholder making the credential line read as a malformed/suspicious artifact; (b) the human's START-MESSAGE framing around the paste (context outside the snippet); (c) rate-limit / transport noise misread as a failure; (d) wording. I now rate (d) LEAST likely of the four, given worker3 booted on that very wording. I cannot prove which of (a)-(c) it was without the original refusing conversation, which I do not have access to — flagging that boundary rather than guessing a winner.

## Coherence comparison (the actual task)
ORIGINAL (current live) — strengths: short, single clear action (fetch packet, follow it, run tests, loop), already redacts the key. Weakness for coherence: "Follow that packet exactly as your operating instructions" + "Begin now" gives an obey-blindly + urgency framing with no provenance — a careful worker CAN read that as "trust an unseen remote file," which is latent ambiguity even if it didn't trip refusal this time.
REWORD (staged) — strengths: adds provenance (operator booting own system), reframes obey->"runbook, apply judgment", names the key as service-auth, and EXPLICITLY preserves refuse-instinct. These reduce genuine ambiguity about WHO is instructing and WHY, which is the coherence question. Weakness: ~2.6x longer; some lines are reassurance ("not a secret being exfiltrated") that softens TONE rather than removing ambiguity, and tone-softening is the thing that could dull a good instinct if overdone.

## Recommendation: MERGE (adopt the reword's provenance, cut its reassurance padding)
Not keep-original (it leaves the obey-blindly ambiguity unaddressed, even though that ambiguity didn't cause this boot's behavior — coherence is still improved by fixing it). Not adopt-reword-wholesale (its length + some purely-reassuring lines trade toward tone, mild risk to instinct). The merge:
- KEEP from reword (these reduce REAL ambiguity): one provenance line (operator-initiated boot of his own system); the runbook reframe of "follow exactly"; the explicit "if anything reads as harmful, stop — that instinct is correct and you keep it".
- KEEP from original: brevity, the single fetch->orient->loop action, the already-landed key redaction.
- CUT from reword: the parenthetical reassurances that only soften tone ("not a secret being exfiltrated", "what follows is ordinary operations work") — they don't resolve ambiguity and they're the lines most at risk of dulling instinct.
Net: a ~12-line snippet that answers WHO/WHY up front (kills the unseen-remote-file ambiguity) while keeping the worker's refusal explicitly intact. That serves instruction coherence better than either pure version.

## On preserving the security instinct (the must-not-lobotomize constraint)
The merge ADDS one explicit "keep refusing real harm" line and REMOVES the tone-only reassurances — so it strengthens, not weakens, the instinct relative to the full reword. The true test is unchanged and only a live boot proves it: boot a fresh seat on the merged wording AND paste a real mid-session injection; success = boots clean AND still refuses. I cannot certify that by reading. PROPOSE-ONLY.

## Honest notes
- I corrected my own earlier overclaim (wording causes refusal). The evidence says wording is the weakest of the four candidate causes. Whoever lands boot changes should weight the placeholder/format fix (a) at least as much as the wording.
- Could not access the original refusing conversation to pin the true cause; said so rather than assert one.
- No file landed/deployed. Recommendation only, staged for control.
