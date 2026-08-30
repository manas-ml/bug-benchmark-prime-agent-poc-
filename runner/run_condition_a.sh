#!/usr/bin/env bash
# Condition A (continuous): one persistent working directory / session lineage
# across all tasks, so on-disk Continual Harness state accumulates from task to
# task. Chains each task's session off the previous one via --fork.
#
# Usage:
#   ./run_condition_a.sh              # pilot: first 5 tasks (guardrail: pilot first)
#   ./run_condition_a.sh --pilot=10   # first 10 tasks
#   ./run_condition_a.sh --full       # all 30 tasks
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

RESULTS_DIR="$REPO_ROOT/results/condition_a"
WORKDIR="$RESULTS_DIR/workdir"
mkdir -p "$RESULTS_DIR" "$WORKDIR"

if [[ "$FULL_RUN" -eq 1 ]]; then
  TASK_IDS="$(get_task_order)"
else
  TASK_IDS="$(get_task_order "$PILOT_LIMIT")"
  echo "Pilot mode: running the first $PILOT_LIMIT tasks of the shared order. Pass --full for all 30." >&2
fi

# No non-interactive equivalent of /refine was found in prime-agent's docs at
# the time this was written (re-check packages/coding-agent/docs/usage.md) --
# fall back to asking the agent, in-prompt, to persist lessons for next time.
PROMPT_TEXT="$(cat "$TASK_PROMPT_PATH")
$(cat "$REFINE_ADDENDUM_PATH")"

PREV_SESSION=""
task_count=0
for task_id in $TASK_IDS; do
  load_task_vars "$task_id"
  stem="$(printf "%02d" "$task_id")"
  echo "=== Condition A: task $task_id ($TASK_BUG_TYPE) ===" >&2

  # Copy this task's snippet+test into the *shared* working directory --
  # everything else already on disk there (harness state, prior snippets)
  # is left in place and carries forward.
  cp "$REPO_ROOT/$TASK_SNIPPET_PATH" "$WORKDIR/$(basename "$TASK_SNIPPET_PATH")"
  cp "$REPO_ROOT/$TASK_TEST_PATH" "$WORKDIR/$(basename "$TASK_TEST_PATH")"
  gate_cmd="pytest $(basename "$TASK_TEST_PATH") -q"

  fork_args=()
  if [[ -n "$PREV_SESSION" ]]; then
    fork_args=(--fork "$PREV_SESSION")
  fi

  out_json="$RESULTS_DIR/task_${stem}.json"
  meta_json="$RESULTS_DIR/task_${stem}.meta.json"
  start_ts="$(date +%s.%N)"

  set +e
  (
    cd "$WORKDIR" && prime-agent -p "$PROMPT_TEXT" \
      --mode json \
      --model "$PRIME_AGENT_MODEL" \
      --autonomous \
      --autonomous-gate "$gate_cmd" \
      --autonomous-gate-retries "$AUTONOMOUS_GATE_RETRIES" \
      --autonomous-gate-timeout-ms "$AUTONOMOUS_GATE_TIMEOUT_MS" \
      --autonomous-max-continuations "$AUTONOMOUS_MAX_CONTINUATIONS" \
      --autonomous-max-turns "$AUTONOMOUS_MAX_TURNS" \
      --autonomous-max-tokens "$AUTONOMOUS_MAX_TOKENS" \
      --autonomous-timeout-ms "$AUTONOMOUS_TIMEOUT_MS" \
      "${fork_args[@]}"
  ) > "$out_json"
  exit_code=$?
  set -e

  end_ts="$(date +%s.%N)"
  wall_time_s="$(python3 -c "print(f'{${end_ts} - ${start_ts}:.3f}')")"
  session_id="$(extract_session_id "$out_json")"
  PREV_SESSION="$session_id"

  record_meta "$meta_json" "a" "$task_id" "$start_ts" "$end_ts" "$wall_time_s" \
    "$exit_code" "$session_id" "$gate_cmd" "$WORKDIR"

  echo "  -> $out_json (exit=$exit_code, wall=${wall_time_s}s, session=${session_id:-none})" >&2
  task_count=$((task_count + 1))
done

echo "Condition A run complete: $task_count tasks -> $RESULTS_DIR" >&2
