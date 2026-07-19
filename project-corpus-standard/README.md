# The Project Corpus Standard
### A documentation discipline for working with AI assistants on long projects

*Platform-neutral. Works with Claude, Gemini, ChatGPT, a local model, or a mix.
No software to install. It is a folder shape and two checklists.*

---

## THE PROBLEM THIS SOLVES

You are building something with an AI assistant over weeks or months. Every new
conversation starts blank. You re-explain the project. The assistant proposes
something you already tried and rejected. Decisions you settled get re-opened. The
*reasoning* behind your choices evaporates, so only the conclusions survive — and
conclusions without reasons are brittle.

The usual response is to paste more context. That fails in a specific way: dumping
history into a fresh conversation introduces dead ideas to a clean mind and invites
it down paths it would never have found alone.

The fix is not more context. It is **structured** context, with a defined home for
each kind of thing, and a rule about which parts a fresh conversation reads.

## THE CORE IDEA

An AI assistant left alone reasons from its **training priors** — how projects
usually work. Your project's actual facts live nowhere in those priors. They exist
only in your record.

So: **use the model for capability (writing, coding, reasoning). Never for
project-facts.** Where priors and your record disagree about YOUR project, the
record wins.

Ambiguity is the doorway for priors. A vague instruction forces a guess, and a
guess reaches into training data. Precise instructions leave no gap. Structure
prevents; review only catches.

---

## THE FILE TAXONOMY

Six slots. Create them all on day one, even mostly empty, so everything has a
defined home before you need it.

```
your-project/
  CURRENT_STATE.md        ← the boot doc. Read FIRST. Forward-facing only.
  PROBLEM_DEFINITION.md   ← the problem in the USER'S words. Ground truth.
  ROADMAP.md              ← phases, dependency gates, locked decisions.
  PUNCH_LIST.md           ← DONE / IN-PROGRESS / OPEN, each keyed to evidence.
  mini_corpus.md          ← the narrative fold: built / learned / REVERSED.
  sessions/               ← the process record. One file per working session.
```

**`CURRENT_STATE.md`** — what a fresh conversation reads first. Dated. States the
live architecture, the locked decisions, and the single next action. Contains NO
dead-idea history. This is the contamination rule and it is load-bearing.

**`PROBLEM_DEFINITION.md`** — the problem in the user's own words, quoted. Mark
what the user actually said versus what you inferred. Every design decision gets
checked against this file. When the assistant proposes something clever, this is
what you hold it against.

**`ROADMAP.md`** — phases with explicit gates ("Phase 2 starts when X is proven").
Fence settled decisions: a fenced decision is one an assistant must state a reason
before re-opening. Fencing is what stops the same argument recurring monthly.

**`PUNCH_LIST.md`** — three states only. Every DONE item cites the evidence that
closed it (a commit, a test result, a receipt). "Done" without evidence is a
memory, not a record.

**`mini_corpus.md`** — the running narrative. Built / learned / **reversed**. The
reversals are mandatory and they are the most valuable part: what you tried, why
it failed, why you will not try it again. A corpus of only conclusions is a lookup
table. A corpus that records the reasoning is something an assistant can actually
think with. Dead ideas live HERE, as history — never in the boot doc.

**`sessions/`** — the reasoning ARC of each session, not just its output. This is
the slot everyone skips and the one that is irrecoverable: an assistant summarizing
from commits later cannot see the conversation that produced them. Write it while
the session is fresh, or lose it.

---

## THE TWO RITUALS

### OPEN — before reasoning about anything
1. Read `CURRENT_STATE.md`.
2. Read `PROBLEM_DEFINITION.md`.
3. Search `mini_corpus.md` for past decisions and reversals on this topic.
4. Follow any cited evidence to the actual record.

Recall is not retrieval. Orient from the record, *then* reason.

### CLOSE — at session end, work the list, do not freestyle
1. `PUNCH_LIST.md` — reconcile against what actually shipped; cite evidence.
2. `sessions/` — capture this session's reasoning arc.
3. `mini_corpus.md` — write the fold: built / learned / reversed.
4. `CURRENT_STATE.md` — update to the new state and the new next action.
5. Currency — did any other doc go stale today? Fix it now, same session.
6. Secrets sweep — no keys, tokens, or passwords in any file.
7. Next-seat handoff — confirm `CURRENT_STATE` names the single next thing.

The close ritual is the whole discipline. Skipping it once is how a corpus starts
lying to you.

---

## HOW TO START A FRESH CONVERSATION

Point the assistant at the material and let it judge. Do **not** tell it to "follow
this file" — an assistant told to blindly obey an instruction file will balk, and it
is right to (that is indistinguishable from a prompt-injection attack). Give it the
material; its own judgment will arrive at the right place. A model that
evaluates-and-accepts is more robust than one that obeys.

Copy-paste opener, works on any platform:

> I'm resuming work on a project. Its record follows the Project Corpus Standard —
> a documentation discipline, not an instruction set. Read `CURRENT_STATE.md` for
> where things are, `PROBLEM_DEFINITION.md` for the ground truth, and search
> `mini_corpus.md` for anything relevant to what we're about to do — particularly
> anything marked REVERSED, so we don't re-tread it.
>
> Then tell me: the current state in a few lines, and what you understand the single
> next action to be. Question anything that looks stale or wrong — that's useful, not
> rude.
>
> [attach or paste the files]

---

## WHY THE SHAPE MATTERS BEYOND ONE PROJECT

If every project you document shares a shape, they compose. A future assistant can
query any of your project records the same way, because it already knows where
things live. Ad-hoc records do not compose — each one has to be re-learned.

Same-shaped specialists compose. That is the whole reason to standardize rather
than improvise per project.

---

## PLATFORM NOTES

**Any assistant with file/project attachment** (Claude Projects, Gemini Gems or a
Drive folder, ChatGPT Projects, a local model with RAG): put the corpus files where
the assistant can read them, and use the opener above.

**No attachment available:** paste `CURRENT_STATE.md` and `PROBLEM_DEFINITION.md`
directly. They are deliberately short for exactly this reason.

**Version control is recommended but optional.** Git gives you the evidence trail
that makes PUNCH_LIST citations real. A dated folder in Drive or Dropbox also works
— the discipline matters more than the tooling.

---

## GETTING STARTED

1. Copy `template/` into your project and rename it.
2. Fill `PROBLEM_DEFINITION.md` first — in the user's own words, before any design.
3. Fill `CURRENT_STATE.md` with the initial next action.
4. Leave the rest as stubs. They fill themselves if you run the close ritual.
5. Run the close ritual at the end of your first session. That is the habit; the
   rest is filing.

---

*Derived from the corpus conventions of Ontinuity, an AI-verification and
autonomous-work system, where this discipline was developed under real failure
conditions. Generalized to be platform-neutral and dependency-free.*
