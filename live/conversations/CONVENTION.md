# CONVERSATION PROVENANCE — live/conversations/

## Purpose
The receipts capture the work; the sessions capture the seat. Neither captures the
operator layer — the dialogue where direction is set, fabrications are caught,
STOPs are authorized, and errata originate. This directory closes that loop:
operator-layer conversation records committed alongside the receipts they produced.

## Rules
1. REDACTION IS MANDATORY. This repo is public. No keys, tokens, or credentials
   may appear in any record — replace with [REDACTED-<kind>]. A record that would
   leak a credential does not get committed until scrubbed.
2. FORM IS DECLARED. Each record states its own fidelity: verbatim, condensed,
   or decision-record. Condensed records quote rulings and directives verbatim;
   narration may be summarized. Full-fidelity exports remain operator-held
   (Claude: Settings -> Privacy -> Export data).
3. LINEAGE IS HONEST. Records name their participants by the standing convention
   (operator name; agent as HARNESS:MODEL) and carry the Assisted-by trailer in
   their commit.
4. CROSS-REFERENCE. Records cite the receipts, deploys, and queue shas they
   produced, so a stranger can walk conversation -> decision -> commit -> receipt.

## Naming
conversations/YYYY-MM-DD_<topic>.md
