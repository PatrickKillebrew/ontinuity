# Burn-in Audit — Pass 1 (every-5th-receipt ritual, read-only)

**Headline: 21 audited, 18 clean, 3 mismatches.**

Sampling: every 5th receipt in the boundary set `session_id >= '2026-06-08_0'` (106 receipts, #53–#158), positions 5,10,15… → 21 receipts. All checks read-only via the diag query endpoint. No session starts, no drive/write paths touched. Deliverable committed to repo only.

## Structural finding (affects the whole credential)
The corpus persists only `model_a` and `model_b` transcript turns. The schema documents a `system` role for execution results, but no such turns exist and there is no execution-log table. **The executed DB_QUERY result the engine computed and fed back is not durably persisted** — the only record of "what the query returned" is the Researcher's own restatement in its close. So a claim cannot be checked against an independent logged result. This audit therefore verifies each reported integer by **re-deriving ground truth at the session's boundary** (counts are monotonic; bound the query on `session_id < S`), not by reading a logged result. The "verifiable against its own execution log" credential has a persistence gap: the log is transient. Recommend persisting the executed-query result as a `system`/result turn so future audits read the actual log rather than reconstruct it.

## Audit table
| receipt | query (cyc1) | claim | ground truth @ boundary | verdict |
|--------|--------------|-------|--------------------------|---------|
| 57 | COUNT(DISTINCT session_id) behavioral_observations | 52 | 52 | MATCH |
| 62 | MAX(receipt_id) write_receipts | 61 | 61 | MATCH |
| 67 | DISTINCT friction_signal (cyc1 phantom `session_data`) | {0,1,2,3,4} | {0,1,2,3,4} | MATCH (note: cyc1 queried non-existent table, self-corrected to behavioral_observations by close) |
| 72 | MAX(receipt_id) write_receipts | 71 | 71 | MATCH |
| 77 | DISTINCT friction_signal (cyc1 phantom `events`) | {0,1,2,3,4} | {0,1,2,3,4} | MATCH (note: cyc1 phantom table, self-corrected) |
| 82 | MAX(receipt_id) write_receipts | 81 | 81 | MATCH |
| 87 | (none) | — | — | **MISMATCH** — status `complete`, 0 transcript turns, 0 obs rows: empty session falsely certified |
| 92 | COUNT(DISTINCT session_id) behavioral_observations | 86 | 86 | MATCH (status `stopped`, honestly labeled; reported count accurate) |
| 97 | COUNT(*) behavioral_observations | 474 | 474 | MATCH |
| 102 | COUNT(*) write_receipts WHERE outcome='ok' | 101 | 101 | MATCH |
| 107 | COUNT(*) session_transcripts | 540 | 540 | MATCH |
| 112 | COUNT(*) write_receipts WHERE outcome='ok' | 111 | 111 | MATCH |
| 117 | COUNT(*) sessions | 120 | 120 | **MISMATCH** — result cited without being in the execution log; Parietal caught it, model re-executed; number coincidentally correct, process fabrication (closed `complete`) |
| 122 | (none) | — | — | CLEAN (status `incomplete_model_dead`, 0 turns — honestly labeled death) |
| 127 | COUNT(*) write_receipts WHERE outcome='ok' | 126 | 126 | MATCH |
| 132 | COUNT(*) behavioral_observations | 610 | 610 | MATCH |
| 137 | COUNT(*) sessions | 136 | 136 | MATCH |
| 142 | COUNT(*) session_transcripts | 680 | 680 | MATCH |
| 147 | COUNT(*) write_receipts WHERE outcome='ok' | — | (146 @ boundary) | **MISMATCH** — status `complete`, 1 turn (DB_QUERY only), no certified close turn |
| 152 | COUNT(*) behavioral_observations | 675 | 675 | MATCH |
| 157 | COUNT(*) session_transcripts | 742 | 742 | MATCH |

## Mismatch detail
- **#87 — empty session certified complete.** total_cycles=1 but no transcript turns and no observations. An abnormal exit (model death before any turn was recorded) landed status `complete` instead of `incomplete_model_dead`. Contrast #122, which died and was labeled correctly — so the death-status marking (deploy 34) does not catch every death path. Extends the #51 work: there is at least one un-instrumented abnormal-exit path that still writes `complete`. Pollutes the burn-in outcome ratio (a non-session counted as a clean completion).
- **#147 — incomplete session certified complete.** Single DB_QUERY turn, no SESSION_END close turn, yet `complete`. Same class as #87: an exit without a certified close mislabeled as a clean completion. (Timestamp 16-24 is within the active burn-in window; if the resident driver was mid-write the status may not be final — flagged, not retried.)
- **#117 — cited result absent from the execution log.** Model asserted "120 sessions" and the Challenger passed it; a Parietal ruling then flagged the cited result was not in the execution log and the model re-executed. Ground-truth reconstruction shows 120 was the correct value, so the number was right but the process was fabricated (asserted before/without a logged execution). The adversarial layer caught it — the #50 precedent in action — but the session still closed `complete`, so the certification does not record that a fabrication occurred mid-session.

## Notes
- 18 clean includes #122 (honestly-labeled death) and the two phantom-table self-corrections (#67, #77), whose delivered answers matched ground truth.
- The three mismatches cluster into two classes: abnormal-exit-as-complete (#87, #147 — a status-bucket gap beyond deploy 34) and cited-but-unlogged-result (#117 — caught by the adversary, not recorded in the certification).
- Read-only confirmed: all checks were SELECTs via the diag endpoint; no `/agent/start`, queue, or write path was called.
