# 2026-10-04 — Control-seat session: the corrected SantaClean build run on the operator's laptop through the hands; Projenius restaffed on MAIN

Form: condensed (operator rulings quoted verbatim; narration summarized). Participants: Patrick (operator); control seat claude.ai-agent:claude-fable-5-1. Seat session 44a78491, contract project `santaclean` (five items). Boot: CONTROL_QUICKBOOT v3.1 from the project corpus: vault read, token minted and verified (PatrickKillebrew), probe 25 ops, five ground reads, bootstrap_gate.

## Why this session happened
The operator had a corrected SantaClean tree (the October 3 correction of a week of GPT/Codex "Astra" work) whose last step needed the laptop: the installed Presidio, spaCy and GLiNER weights, the validation Python and the September 24 freeze recipe live only there. The operator: "Astra was able to use the hands that I built for the laptop work to do the testing it performed for its session. You can use those hands as well to take care of the work in my laptop. Instructions are in the corpus if you have problems. The laptop is up and running."

## Boot facts
- bootstrap_gate first returned 409 contention: a control session `openai-chat:codex/root` opened 2026-09-23T13:21Z had never closed. Passed takeover:true; the gate closed it as a takeover.
- Second run: six of seven checks passed; STAFFING failed: Projenius `deepseek/deepseek-v3.2` at Novita returned 404 MODEL_NOT_FOUND. Novita's model list that hour carried deepseek_v3, deepseek-v4-flash, deepseek-v4-pro, deepseek-v4.1-flash and the R1 family, no v3.2. The seat laid out the options and stopped, because the punch list records MAIN variable changes as the operator's call.
- Ruling: `deepseek/deepseek_v3`. Set through `railway_set_var` (PROJENIUS_MODEL), engine redeployed, third gate run 7/7, oriented:true, key issued. Staffing fact returned: model_b qwen-3.8-27b alive; model_c meta-llama/llama-3.1-8b-instruct alive; parietal gpt-oss-120b alive; projenius deepseek/deepseek_v3 alive.
- orient on "SantaClean laptop build real models freeze": 0 hits in 34 files (the Astra session left no record). orient on "laptop": 18 hits; the protocol is `live/box/laptop_seat.py` (commit 4af7b8b3): task body JSON `{"op":"run"|"read"|"write"|"ping"}`, scope C:\donkeycar, run prefix whitelist, 120 s run timeout, result posted as kind=result with reply_to; fetch by reply_to and ACK at once.

## What was done through the hands (all mailbox task ids in the ledger)
1. ping (scope C:\donkeycar); config read (whitelist: python, pip, dir, type, copy, git, …); inventory of the September 24 build root and `operator-candidate-1` (35 fingerprinted model files, wheel cache, validation Python 3.11 at the operator's Downloads kit).
2. A staging script (260 KB, the corrected tree as a base64 zip with a SHA-256 manifest) written to C:\donkeycar and verified by hash after CRLF normalization (the laptop seat writes text mode). It created a new root `santaclean-build-20260924\corrected-20261004-N`, hard-linked the models from `operator-candidate-1` after fingerprint checks, copied wheels and assets, verified every source file, and launched a detached `job.py` with a progress file, because the seat's 120 s timeout cannot hold a freeze.
3. Root -1: `tests/test_cleaned_copy_real_models.py` under the installed models FAILED: the detectors flag the Safe Harbor form `762XX` itself, so the strict residual reviewer blanked every ZIP. Fix: a postal column already in three-digit form is the output (SantaClean commit 986edee, regression test).
4. Root -2: FAILED: spaCy labels the lone word "Weekends" LOCATION (and "Overnight" DATE_TIME) at its fixed 0.85, blanking availability. A detector probe over 37 values grounded the rule. Fix: a single dictionary word from a model is not a place or a date element; month names and holidays stay dates; gazetteer places (0.99), street and coordinate rules, and names untouched (SantaClean commit 28f5605, regression test).
5. Root -3 (commit 28f5605): real-model test OK (1 test, 21.6 s; two questions, "Client" and "Backup caregiver" at 0.6; zero residual flags; 18-category record). Freeze WINDOWS_FREEZE_PASSED in 563 s: `SantaClean.exe` 75,394,329 bytes, SHA-256 09e47c349dbacf77c434c48f17d0c81d960ce32601868c243c4791bc3ed920d2; bundle 16,892 files, 1,512,896,889 bytes. Installer built: `SantaClean-Validation-Setup.exe` 740,032,319 bytes, SHA-256 d4f299ce2036858def4b2032450361f66e98c50ef0216e2a18b98128385e9037. Frozen start: 45 s alive with an isolated profile, no stderr, private store created. `Start-SantaClean.cmd` and `README-OPERATOR-RUN.txt` left in the root for the operator's run.
6. Delivered to the operator: `SantaClean-corrected-2026-10-04.zip` (SantaClean commit 127378a, docs carrying the fingerprints) and RESUME-HERE.

## Findings worth keeping
- The laptop seat is a 120 s, prefix-whitelisted shell. Anything longer runs as a detached job started by a `python C:\donkeycar\<stage>.py` task, reporting through a progress file read by `read` tasks. Astra's September job used the same shape; it is now in the manual.
- Text written through the laptop seat lands with CRLF; verify hashes after normalization, and never assume byte identity for binary content.
- A Bash poll that exceeds the sandbox's own two-minute limit dies after the task is sent and before the ACK, leaving one result queued. One such result (1a0518a0, the pyinstaller.log read) was claimed and ACKed before close. Control's inbox also holds 19 historical queued messages (2026-06-30 and 2026-09-04..09, worker signoffs and results from retired work); left in place, not purged.
- Known installed-model behaviour recorded in the SantaClean tree, not changed: a name that is also a Census place (Rose, Baker, Lee, Katherine) is coded in a name column but removed, not coded, inside free text; capitalized common words that are also places (Park, Lake, North, Spring, Home) are removed in free text. Safe direction.

## Deviations, stated
- The SantaClean commits live in a local repository in the seat's sandbox and in the delivered zip, not in this corpus; the private `santaclean` repository is the operator's next step. The corpus records cite their shas and the fingerprints.
- The frozen build was started once on the operator's laptop (an isolated profile, killed after 45 s) as a start-up check; no UI was driven, because the September UI driver targets screens the correction removed.

## Left open
- Operator: run `Start-SantaClean.cmd` once start to finish on an invented CSV; rule on the result (contract item `manual-run`, CARRIED). Then one real export, the private repository, the license decision, code signing.
- Astra's 2026-09-23 control session left no conversation record, fold or punch-list entry; its work is on the laptop under the dated `santaclean-*` roots and in the operator's zip.

Cross-refs: seat session 44a78491; contract `santaclean` items laptop-inventory, stage-tree, real-model-test, freeze (DONE), manual-run (CARRIED); SantaClean commits 986edee, 28f5605, 127378a; laptop roots corrected-20261004-1/2/3; receipt at GET /agent/handoff.
