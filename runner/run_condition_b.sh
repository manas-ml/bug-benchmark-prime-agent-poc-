#!/usr/bin/env bash
# Condition B (baseline): fresh `mktemp -d` working directory per task, no
# --fork -- nothing persists between tasks. Same model, prompt template, and
# gate budgets as Condition A so model/config choice is not a confound.
#
# Usage:
#   ./run_condition_b.sh              # pilot: first 5 tasks (guardrail: pilot first)
#   ./run_condition_b.sh --pilot=10   # first 10 tasks
#   ./run_condition_b.sh --full       # all 30 tasks
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"
require_prime_agent

FULL_RUN=0
PILOT_LIMIT=5
for arg in "$@"; do
  case "$arg" in
    --full) FULL_RUN=1 ;;
    --pilot=*) PILOT_LIMIT="${arg#--pilot=}" ;;
    *) echo "unknown argument: $arg" >&2; exit 1 ;;
  esac
done

RESULTS_DIR="$REPO_ROOT/results/condition_b"
mkdir -p "$RESULTS_DIR"

if [[ "$FULL_RUN" -eq 1 ]]; then
  TASK_IDS="$(get_task_order)"
else
  TASK_IDS="$(get_task_order "$PILOT_LIMIT")"
  echo "Pilot mode: running the first $PILOT_LIMIT tasks of the shared order. Pass --full for all 30." >&2
fi

PROMPT_TEXT="$(cat "$TASK_PROMPT_PATH")"

task_count=0
for task_id in $TASK_IDS; do
  load_task_vars "$task_id"
  stem="$(printf "%02d" "$task_id")"
  echo "=== Condition B: task $task_id ($TASK_BUG_TYPE) ===" >&2

  workdir="$(mktemp -d -t bug-poc-condb-XXXXXX)"
  cp "$REPO_ROOT/$TASK_SNIPPET_PATH" "$workdir/$(basename "$TASK_SNIPPET_PATH")"
  cp "$REPO_ROOT/$TASK_TEST_PATH" "$workdir/$(basename "$TASK_TEST_PATH")"
  gate_cmd="pytest $(basename "$TASK_TEST_PATH") -q"

  out_json="$RESULTS_DIR/task_${stem}.json"
  meta_json="$RESULTS_DIR/task_${stem}.meta.json"
  start_ts="$(date +%s.%N)"

  set +e
  (
    cd "$workdir" && prime-agent -p "$PROMPT_TEXT" \
      --mode json \
      --model "$PRIME_AGENT_MODEL" \
      --autonomous \
      --autonomous-gate "$gate_cmd" \
      --autonomous-gate-retries "$AUTONOMOUS_GATE_RETRIES" \
      --autonomous-gate-timeout-ms "$AUTONOMOUS_GATE_TIMEOUT_MS" \
      --autonomous-max-continuations "$AUTONOMOUS_MAX_CONTINUATIONS" \
      --autonomous-max-turns "$AUTONOMOUS_MAX_TURNS" \
      --autonomous-max-tokens "$AUTONOMOUS_MAX_TOKENS" \
      --autonomous-timeout-ms "$AUTONOMOUS_TIMEOUT_MS"
  ) > "$out_json"
  exit_code=$?
  set -e

  end_ts="$(date +%s.%N)"
  wall_time_s="$(python3 -c "print(f'{${end_ts} - ${start_ts}:.3f}')")"

  record_meta "$meta_json" "b" "$task_id" "$start_ts" "$end_ts" "$wall_time_s" \
    "$exit_code" "" "$gate_cmd" "$workdir"

  echo "  -> $out_json (exit=$exit_code, wall=${wall_time_s}s, workdir=$workdir)" >&2
  task_count=$((task_count + 1))
done

echo "Condition B run complete: $task_count tasks -> $RESULTS_DIR" >&2
echo "Note: per-task temp workdirs under \$TMPDIR are left in place (not auto-cleaned)" >&2
echo "so scoring can inspect the agent's edits; remove them yourself once scored." >&2
