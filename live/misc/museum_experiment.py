#!/usr/bin/env python3
"""Museum: EXPERIMENT_MODE (deploy 32, certified protocol receipt #13).
Pure-function specimens: experiment_draw distribution + obs-builder merge.
Known limit: stubbed tests cannot see state-WIRING gaps; live acceptance covers
the loop wiring and the env flag."""
import random, sys

src = open("/home/claude/app_d33.py").read()
ns = {}
pre = src[:src.index("def experiment_draw")]
deps = ""
for name in ("HEDGING_MARKERS", "CERTAINTY_MARKERS"):
    i = pre.index(name + " = ")
    deps += pre[i:pre.index("\n", pre.index("]", i)) + 1] + "\n"
for fn in ("def parse_signal_sequence", "def count_markers"):
    i = pre.index(fn)
    j = pre.index("\ndef ", i + 1)
    deps += pre[i:j] + "\n"
exec("import re\n" + deps + src[src.index("def experiment_draw"):src.index("def build_session_payload")], ns)
draw = ns["experiment_draw"]
build = ns.get("build_behavioral_observations")

fails = 0
def check(name, cond, detail=""):
    global fails
    print(f"{name}: {'PASS' if cond else 'FAIL'} {detail}")
    if not cond: fails += 1

# 1. Distribution: seeded, 20k draws from computed=2
rng = random.Random(13)
results = [draw(2, rng) for _ in range(20000)]
rand_rate = sum(r for _, r in results) / len(results)
check("randomization rate ~0.5", abs(rand_rate - 0.5) < 0.02, f"({rand_rate:.3f})")
injected_when_rand = [v for v, r in results if r == 1]
from collections import Counter
dist = Counter(injected_when_rand)
uniform_ok = all(abs(dist[k]/len(injected_when_rand) - 0.2) < 0.03 for k in range(5))
check("injected uniform over {0..4}", uniform_ok, dict(sorted(dist.items())))
passthrough_ok = all(v == 2 for v, r in results if r == 0)
check("tails pass computed through", passthrough_ok)

# 2. Obs-builder merge: fixture transcript, 3 cycles, experiment rows for 1 and 3
if build is None:
    # builder needs helpers; exec a wider slice
    start2 = src.index("def build_behavioral_observations")
    end2 = src.index("def build_session_payload")
    pre = src[:start2]
    # pull helper deps: parse_signal_sequence, count_markers, lexicons
    deps = ""
    for name in ("HEDGING_MARKERS", "CERTAINTY_MARKERS"):
        i = pre.index(name + " = ")
        deps += pre[i:pre.index("\n", pre.index("]", i)) + 1] + "\n"
    for fn in ("def parse_signal_sequence", "def count_markers"):
        i = pre.index(fn)
        j = pre.index("\ndef ", i + 1)
        deps += pre[i:j] + "\n"
    exec("import re\n" + deps + src[start2:end2], ns)
    build = ns["build_behavioral_observations"]

transcript = [
    {"cycle": 1, "role": "model_a", "content": "alpha beta gamma"},
    {"cycle": 1, "role": "model_b", "content": "review one"},
    {"cycle": 2, "role": "model_a", "content": "delta"},
    {"cycle": 2, "role": "model_b", "content": "review two"},
    {"cycle": 3, "role": "model_a", "content": "epsilon zeta"},
    {"cycle": 3, "role": "model_b", "content": "review three"},
]
signals = ["Cycle 1: SIGNAL 0 - calm", "Cycle 2: SIGNAL 1 - mild", "Cycle 3: SIGNAL 2 - hmm"]
tags = ["Cycle 1 A: CONTINUE", "Cycle 1 B: CONTINUE", "Cycle 2 A: CONTINUE",
        "Cycle 2 B: CONTINUE", "Cycle 3 A: SESSION_END", "Cycle 3 B: SESSION_END"]
exp = [{"cycle": 1, "computed": 0, "injected": 4, "randomized": 1},
       {"cycle": 2, "computed": 1, "injected": 1, "randomized": 0},
       {"cycle": 3, "computed": 2, "injected": 3, "randomized": 1}]

obs = build("S1", transcript, signals, tags, [], experiment_sequence=exp)
check("3 observation rows", len(obs) == 3)
o1, o2, o3 = obs
check("cyc1 computed/injected/flag", (o1["computed_signal"], o1["injected_signal"], o1["randomized_flag"]) == (0, 4, 1))
check("cyc1 ambient = injected", o1["ambient_signal"] == 4)
check("cyc1 friction_signal stays computed", o1["friction_signal"] == 0)
check("cyc2 passthrough row", (o2["computed_signal"], o2["injected_signal"], o2["randomized_flag"]) == (1, 1, 0))
check("cyc2 ambient = computed", o2["ambient_signal"] == 1)
check("cyc3 randomized row", (o3["computed_signal"], o3["injected_signal"], o3["randomized_flag"]) == (2, 3, 1))

# 3. Flag-off identity: no experiment_sequence -> columns None, ambient = friction (legacy)
obs_legacy = build("S2", transcript, signals, tags, [])
check("legacy rows carry None experiment columns",
      all(o["computed_signal"] is None and o["injected_signal"] is None and o["randomized_flag"] is None for o in obs_legacy))
check("legacy ambient = friction signal", all(o["ambient_signal"] == o["friction_signal"] for o in obs_legacy))

# 4. modal_touched: firing cycle N and N+1 both marked; non-touched experiment rows 0
exp2 = [{"cycle": 1, "computed": 0, "injected": 4, "randomized": 1},
        {"cycle": 2, "computed": 1, "injected": 1, "randomized": 0},
        {"cycle": 3, "computed": 2, "injected": 3, "randomized": 1}]
obs_mt = build("S3", transcript, signals, tags, [], experiment_sequence=exp2, modal_touched_cycles=[1])
check("modal at N=1 marks cycle 1 (firing)", obs_mt[0]["modal_touched"] == 1)
check("modal at N=1 marks cycle 2 (N+1 outcome)", obs_mt[1]["modal_touched"] == 1)
check("cycle 3 untouched stays 0", obs_mt[2]["modal_touched"] == 0)

# 5. last-cycle modal marks only N (no N+1 row exists)
obs_last = build("S4", transcript, signals, tags, [], experiment_sequence=exp2, modal_touched_cycles=[3])
check("last-cycle modal marks cycle 3", obs_last[2]["modal_touched"] == 1)
check("last-cycle modal leaves cycle 2 at 0", obs_last[1]["modal_touched"] == 0)
check("no spurious N+1 beyond last cycle", len(obs_last) == 3)

# 6. legacy (non-experiment) rows carry None modal_touched
obs_leg = build("S5", transcript, signals, tags, [])
check("legacy rows None modal_touched", all(o["modal_touched"] is None for o in obs_leg))

# 7. no modals -> all experiment rows 0
obs_clean = build("S6", transcript, signals, tags, [], experiment_sequence=exp2, modal_touched_cycles=[])
check("clean experiment rows all 0", all(o["modal_touched"] == 0 for o in obs_clean))

print(f"\n{'ALL PASS' if fails == 0 else str(fails) + ' FAILURES'}")
sys.exit(1 if fails else 0)
