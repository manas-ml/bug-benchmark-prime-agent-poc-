# Bug-Finding Benchmark for Prime Agent's Continual Harness

A PoC that tests whether Prime Agent's Continual Harness produces a real accuracy/cost
improvement curve across a batch of independent bug-finding tasks, versus a state-wiped
baseline on the same tasks.

- **Condition A (continuous):** one Prime Agent session lineage (`--fork`-chained, shared
  working directory) across all 30 tasks, so on-disk Continual Harness state accumulates.
- **Condition B (baseline):** the same 30 tasks, same model, fresh working directory and
  session per task -- nothing carries over.

If Condition A's `found`-rate trends upward (or its cost trends downward) relative to
Condition B's flat line, that's evidence the harness is learning something transferable
-- not just the model being generally competent.

## Before running at scale

This scaffold's runner scripts target `prime-agent`'s CLI as documented in
`PrimeIntellect-ai/prime-agent`'s `packages/coding-agent/docs/usage.md` and `json.md` at
the time this was written: `-p` for one-shot prompts, `--mode json` for the JSON-lines
event stream, `--autonomous`/`--autonomous-gate`/`--autonomous-gate-retries` for
host-verified unattended runs with a bounded retry budget (default 3), `--fork
<path|id>` for session lineage, and `--model <pattern>` to pin a model (list candidates
with `prime-agent model list`). **CLI details can drift between versions** -- re-verify
every flag against the live `prime-agent --help` / `docs/usage.md` before running the
full 30-task x 2-condition batch. `runner/common.sh` fails fast with a clear error if
`prime-agent` isn't on `PATH` or `PRIME_AGENT_MODEL` isn't set, but it cannot detect a
renamed/removed flag on its own.

No non-interactive equivalent of the interactive `/refine` command was found in the
docs at the time of writing. Condition A works around this by appending an explicit
"persist a lesson to your durable notes/skills" instruction to its prompt
(`runner/prompts/refine_addendum.md`) instead of invoking `/refine` directly -- check
again in case a later CLI version adds one.

## Repo layout

```
corpus/
  generate_corpus.py     deterministic, AST-located bug injector
  snippets/               30 x (NN_clean.py, NN_buggy.py, NN_test.py)
  tasks.jsonl             one line per task: ground truth
  task_order.json         seeded shuffle of task ids, shared by both conditions
runner/
  common.sh               shared config/helpers (model, autonomous budgets, task lookup)
  run_condition_a.sh
  run_condition_b.sh
  prompts/task_prompt.md
  prompts/refine_addendum.md
  lib/get_task.py, lib/get_task_order.py
scoring/
  score_task.py           scores one task's run against ground truth
  aggregate.py            rolls every task+condition into results/aggregate.csv
analysis/
  plot_results.py         rolling-average overlay charts + first10-vs-last10 summary
results/                  raw session exports + score CSVs + charts land here (gitignored)
```

## How the corpus works

`corpus/generate_corpus.py` defines 30 small, self-contained, hand-written Python
functions (no two share logic) with companion pytest files. Each snippet is assigned
exactly one bug type, round-robin over a fixed 7-type taxonomy (off-by-one, wrong
comparison operator, missing `is not None` check, wrong/shadowed variable, missing
`int()`/`str()` cast, mutable default argument, incorrect index/slice bound) -- 5
occurrences each for the first two types, 4 for the rest, spread evenly rather than
clustered.

For each snippet, the matching mutator:
1. Parses the clean source with `ast` and locates the single node matching that bug
   type's pattern (e.g. the sole `range(...)` call, the sole simple `Compare`, the sole
   `if x is not None:` guard with no `else`) -- and raises if the match isn't unique, so
   a design mistake fails loudly instead of injecting into the wrong spot.
2. Replaces only that node's exact source span with the buggy text (a precise text
   splice keyed off the node's line/column, not a full `ast.unparse` regeneration), so
   formatting elsewhere is untouched and the reported `bug_line` is exact.
3. Is verified twice via a real `pytest` subprocess: the untouched clean version must
   pass the companion test, and the mutated version must fail it. Generation aborts if
   either check fails.

Run it with:

```
python3 corpus/generate_corpus.py               # seed=1337 by default
python3 corpus/generate_corpus.py --seed 4242    # a different corpus/task-order pairing
```

This (re)writes `corpus/snippets/*.py`, `corpus/tasks.jsonl`, and `corpus/task_order.json`.

## Running the experiment

Requires `prime-agent` installed, authenticated, and on `PATH`; Python 3.10+; `pytest`
(`pip install -r requirements.txt`).

```bash
export PRIME_AGENT_MODEL="provider/model-id"   # from `prime-agent model list`; identical for both conditions

# Pilot first (guardrail): 5 tasks through both conditions end to end, to sanity-check
# the pipeline and catch prompt issues cheaply before spending on the full 30.
./runner/run_condition_a.sh
./runner/run_condition_b.sh

# Estimate cost from the pilot, set a hard budget, then:
./runner/run_condition_a.sh --full
./runner/run_condition_b.sh --full
```

Each task-run writes `results/condition_X/task_NN.json` (the raw `--mode json`
transcript) and `results/condition_X/task_NN.meta.json` (a sidecar the runner writes
itself: wall-clock start/end/duration, exit code, the preserved working directory, and,
for Condition A, the forked session id) -- both files are required by scoring.

Condition A reuses a single working directory (`results/condition_a/workdir/`) for the
whole lineage, by design. Condition B uses a fresh `mktemp -d` per task and does **not**
auto-clean them, since scoring needs to inspect the agent's on-disk edits; clean them up
yourself once scored. Keep the two conditions' directories/sessions strictly separate --
any accidental shared state between them invalidates the comparison.

Both runners consume the same `corpus/task_order.json` shuffle, so ordering is not a
confound between conditions. If budget allows, rerun the whole experiment with a second
`--seed` to check the curve isn't an ordering artifact.

## Scoring and analysis

```bash
python3 scoring/aggregate.py                       # -> results/aggregate.csv
pip install -r analysis/requirements.txt
python3 analysis/plot_results.py                    # -> results/found_rate_rolling.png,
                                                      #    results/cost_rolling.png,
                                                      #    + first10-vs-last10 summary on stdout
```

`aggregate.py` skips (with a stderr warning, not a fabricated row) any task/condition
pair that hasn't been run yet, so it's safe to run against a partial (pilot) result set.

**`found`** is determined authoritatively by re-running the task's own checker
(`pytest ..._test.py`) against the preserved working directory from `meta.json` --
not by parsing the transcript. A task counts as found only if the checker now passes
*and* the reported `FINAL_ANSWER: line=...` is within 1 line of the ground-truth
`bug_line`. `correct_location` requires an exact line match. `false_positives` is a
heuristic count of other "line N" mentions in the agent's final message.

**Known gap:** `prime-agent`'s `--mode json` schema (per `json.md` at the time of
writing) does not document a token-usage event, so `tokens_used` is extracted
best-effort by scanning the transcript for any token-count-looking field and may be
`None`. `wall_time_s` does **not** depend on that schema -- it's timed directly by the
runner scripts and is reliable regardless of transcript format. Re-inspect a real
transcript once you have `prime-agent` running live and tighten
`scoring/score_task.py::extract_tokens_used` if a proper usage event exists.

## Guardrails already baked in

- Runners default to a 5-task pilot; pass `--full` only after sanity-checking output.
- `--autonomous-gate-retries` (and the other `--autonomous-*` budget flags) are set
  explicitly and identically by `runner/common.sh` for both conditions.
- `PRIME_AGENT_MODEL` is a single required env var read by both runners, so model choice
  can't silently drift between them.
- Task order is shuffled once (`corpus/task_order.json`) and consumed identically by
  both runners.
