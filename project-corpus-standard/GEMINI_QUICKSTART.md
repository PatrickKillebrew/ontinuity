# Quickstart — Gemini

*Ten minutes. Two options depending on how you like to work.*

---

## OPTION A — Google Drive folder (recommended)

Gemini reads from Drive, so your corpus lives in a folder and stays current
without re-uploading.

1. Create a Drive folder named for your project.
2. Copy the six files from `template/` into it. Rename `<PROJECT NAME>` throughout.
3. Fill `PROBLEM_DEFINITION.md` FIRST — in your own words, before any design talk.
   Quote yourself literally; do not tidy it into requirements language.
4. Fill `CURRENT_STATE.md` with what exists today and the single next action.
5. Leave the other four as stubs. They fill themselves if you run the close ritual.

**Starting a session:** open Gemini, attach the folder (or the two files above),
and paste the opener from the main README.

**Ending a session:** paste the close ritual and let Gemini draft the updates. Read
what it writes before saving — the ritual is yours, the drafting is its job.

---

## OPTION B — A Gem

If you want the discipline baked in so you don't paste it each time, create a Gem
with these instructions:

> You are working on a long-running project documented under the Project Corpus
> Standard. Before reasoning about any task, orient by reading `CURRENT_STATE.md`
> (what exists now, and the single next action), `PROBLEM_DEFINITION.md` (the
> problem in the user's own words — the authority every decision is checked
> against), and searching `mini_corpus.md` for prior decisions and REVERSALS on the
> topic at hand.
>
> Recall is not retrieval. Reason from the record, not from what you generally know
> about how projects like this work. Where your general knowledge and the record
> disagree about THIS project, the record wins. Use your general capability freely
> for writing, coding, and reasoning — but never for facts about this project.
>
> If something in the record looks stale, wrong, or self-contradictory, say so.
> Questioning the record is useful, not rude. If you cannot find something, say you
> cannot find it — never fill the gap with a plausible guess. A guess that looks
> right is worse than an admitted gap, because it cannot be caught.
>
> At session close, run the close ritual: reconcile the punch list against what
> actually shipped, write the session's reasoning arc to `sessions/`, write the
> fold (built / learned / reversed) to `mini_corpus.md`, update `CURRENT_STATE.md`
> to the new state and next action, fix anything that went stale, sweep for
> secrets, and confirm the next action is stated in one line.

Attach the corpus folder to the Gem. Now every conversation starts oriented.

---

## THE ONE HABIT THAT MATTERS

Run the close ritual. Once.

Everything else in this standard is filing. The close ritual is the thing that
makes the filing exist. A corpus that is written only when you remember to write
it will be wrong within a month, and a corpus that is wrong is worse than none —
you will trust it.

---

## A NOTE ON WHAT TO EXPECT

The first session feels like overhead. The third session is when it pays: you open
a fresh conversation, it reads the record, and it knows things you had forgotten
you decided. The reversals are what surprise people — an assistant that says "you
tried that in fold 003 and it failed because X" is doing something no amount of
context-pasting achieves.
