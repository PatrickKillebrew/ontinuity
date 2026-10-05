# 2026-10-05 — Control-seat session: the operator's first walk through the SantaClean build, three fixes, rebuilt on the laptop

Form: condensed (operator words quoted verbatim; narration summarized). Participants: Patrick (operator); control seat claude.ai-agent:claude-fable-5-1. Seat session f201a27f, contract project `santaclean` (three items). Boot: token verified (PatrickKillebrew), probe 25 ops, five ground reads, bootstrap_gate 7/7 (no contention; projenius deepseek/deepseek_v3 alive). orient "SantaClean walk-through sharing review": 0 hits.

## What the operator found on the first walk (verbatim)
"When I selected a fake file to process, it started evaluating that file without stating that it was actually working. There was nothing to let me know that work had started. I tried to upload the file again but the upload window forbade it, then the 'review what gets removed' page popped up and let me know that work had begun."
"'Your cleaned copy' page sure did pop up fast. It felt like nothing was actually cleaned, even though it probably was. What is the 'owner's sharing review?' That was not part of the original SantaClean. It looks complicated, especially for a non-tech user. Hmm, did you even do a check to see if the software was actually usable by a non-tech user?"

The seat's answer: no. The verification had been 195 engine tests, 56 scripted DOM scenarios against the HTML with a fake back end, the installed-model engine test and a 45-second launch; no person had walked the screens. Both findings were defects.

## Diagnosis and fixes (SantaClean commit 79b8189)
1. No sign of work after choosing a file. `open_dialog` opened the picker, read the file and scanned the column headings for identifiers; the heading scan is what loads the three detection models on the first file (20 to 90 s on the laptop), and the UI's overlay only started after that call returned. The Choose button was disabled meanwhile, which is why the second attempt was refused. Fix: the picker is one call (`open_dialog`, returns at once), the read and heading check another (`load_file`, progress phase `load`), and the overlay shows from the moment the picker closes: "Reading your file and starting the detectors; the first file takes longest while the detection models load."
2. The result screen showed nothing. Cleaning a few rows takes well under a second once the models are warm; the page now says what was done from the applied transform counts (`resolve_and_finalize()["done"]`: rows, columns, "Names: 10 coded, Dates: 9 reduced to the year, Places / addresses: 6 removed (a state stays; a ZIP keeps its first three digits), Phone numbers: 4 coded, Other ID numbers: 3 coded, Ages: 2 kept through 89, 90+ above"; kept columns; the weekday/skills note).
3. The owner's sharing review. The operator asked: "What is needed here to meet the goals we set when we first started building this software? Does this add any value?" Grounded answer: the original design (the SHS sanitizer notes in the project: "she declares; the tool enforces; the ledger proves") has no such form; HHS defines actual knowledge as "clear and direct knowledge" with four examples, requires no documentation for Safe Harbor (Expert Determination needs it), and treats de-identified data as no longer PHI. The form documented something nobody requires, in compliance language, in front of a non-technical operator; its one real point (an unusual detail in a note) is already the review step. Verdict given and acted on: removed, with `release_review.py`, its tests, the shell endpoints, the run-record methods and the history column. One plain sentence stands in its place on the result screen; the processing record states the condition is the organization's own. Both sides were stated: the form did bind a human look to the exact output bytes, and the recipient here is family (the HHS "relative in the data" example); that is a conversation between the owner and the developer, not a screen. Separately noted for the owner: whether her agency is a HIPAA covered entity at all is her question; the tool follows Safe Harbor either way.

Suites after the change: 187 tests (181 pass, 5 Windows skips, the known Python 3.12-only tempfile failure), 56 DOM scenarios including the new load-phase and result-summary checks.

## Rebuild on the laptop (root corrected-20261005-4, through the laptop seat)
- The laptop seat was not polling when the staging task was sent (last laptop message was the previous day's); the task sat queued until the operator restarted the laptop ("The laptop is back up again."), then ran by itself. Lesson: a queued task survives a seat outage and executes on return; check `mailbox_peek status:queued` for the laptop before sending more.
- Real-model end-to-end test: OK, 90.0 s with cold models; same two questions (Client 0.605, Backup caregiver 0.635); zero residual flags; the what-was-done block printed above.
- Freeze: WINDOWS_FREEZE_PASSED in 1280 s (slower than the 563 s of the day before; cold disk after reboot); SantaClean.exe 75,389,090 bytes, SHA-256 3c6cff7698e0a54d8789d7eff8678f51cf15af18d84c392be41d4dfb91c8d5b2; bundle 16,891 files.
- Installer: SantaClean-Validation-Setup.exe 740,003,238 bytes, SHA-256 ef8b85fddb5ab54c23270dc35c64aaf9eb4031ea11a266e23edab446008f9382.
- Frozen start with an isolated profile: alive at 5/15/30/45 s, no stderr, private store created.
- Launcher: C:\donkeycar\santaclean-build-20260924\corrected-20261005-4\Start-SantaClean.cmd. Delivered to the operator: SantaClean-corrected-2026-10-05.zip (commit 79b8189).
- Two sandbox polls exceeded the sandbox's own two-minute limit and left one laptop result queued each time; both were claimed by reply_to or newest-first and ACKed at once.

## Deviations, stated
- The staging task was sent before the seat was known to be down; it queued rather than failing, so nothing was lost, but the send-then-check order was wrong. The manual's LAPTOP HANDS section now says to peek the laptop's queue first.

## Left open
- Operator: second walk through corrected-20261005-4 and ruling (contract item `owner-rerun`, CARRIED).
- Then: one real export, the private `santaclean` repository (tree = commit 79b8189), the license decision, code signing.

Cross-refs: seat session f201a27f; contract `santaclean` items walkthrough-fixes, rebuild (DONE), owner-rerun (CARRIED); corpus commits this session: punch list f1ed8d6, manual fceaa0e, handoff 5671144, queue fold fbe84da; SantaClean commit 79b8189; laptop root corrected-20261005-4; previous record 2026-10-04_santaclean-laptop-run-and-projenius-restaffing.md; receipt at GET /agent/handoff.
