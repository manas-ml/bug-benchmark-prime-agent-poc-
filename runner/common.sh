#!/usr/bin/env bash
# Shared configuration and helpers for run_condition_a.sh / run_condition_b.sh.
# Sourced, not executed directly.
#
# CLI flags below (`-p`, `--mode json`, `--autonomous`, `--autonomous-gate`,
# `--autonomous-gate-retries`, `--fork`, `--model`) were verified against
# PrimeIntellect-ai/prime-agent's packages/coding-agent/docs/usage.md at the time
# this scaffold was written. Re-verify with `prime-agent --help` / the live
# usage.md before running at scale -- CLI details can drift between versions.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- Model: pin identically across both conditions; model choice must not be a
# confound. Set PRIME_AGENT_MODEL in your environment, e.g.:
#   prime-agent model list          # find an exact pattern
#   export PRIME_AGENT_MODEL="provider/model-id"
PRIME_AGENT_MODEL="${PRIME_AGENT_MODEL:-}"

# --- Autonomous budgets: identical for both conditions (guardrail: identical
# retry/turn/token/time budgets so neither condition gets more "tries").
# Defaults below mirror usage.md's own documented defaults; set explicitly
# anyway so a future CLI version changing its defaults can't silently skew
# the comparison between conditions run at different times.
AUTONOMOUS_GATE_RETRIES="${AUTONOMOUS_GATE_RETRIES:-3}"
AUTONOMOUS_GATE_TIMEOUT_MS="${AUTONOMOUS_GATE_TIMEOUT_MS:-300000}"
AUTONOMOUS_MAX_CONTINUATIONS="${AUTONOMOUS_MAX_CONTINUATIONS:-3}"
AUTONOMOUS_MAX_TURNS="${AUTONOMOUS_MAX_TURNS:-12}"
AUTONOMOUS_MAX_TOKENS="${AUTONOMOUS_MAX_TOKENS:-80000}"
AUTONOMOUS_TIMEOUT_MS="${AUTONOMOUS_TIMEOUT_MS:-1800000}"

TASK_PROMPT_PATH="$REPO_ROOT/runner/prompts/task_prompt.md"
REFINE_ADDENDUM_PATH="$REPO_ROOT/runner/prompts/refine_addendum.md"

get_task_order() {
  # $1: limit (optional) -- prints space-separated task ids
  local limit="${1:-}"
  if [[ -n "$limit" ]]; then
    python3 "$REPO_ROOT/runner/lib/get_task_order.py" --limit "$limit"
  else
    python3 "$REPO_ROOT/runner/lib/get_task_order.py"
  fi
}

load_task_vars() {
  # $1: task id -- sets TASK_SNIPPET_PATH, TASK_TEST_PATH, TASK_BUG_TYPE,
  # TASK_BUG_LINE, TASK_CHECKER_CMD in the calling shell.
  eval "$(python3 "$REPO_ROOT/runner/lib/get_task.py" "$1")"
}

require_prime_agent() {
  if ! command -v prime-agent >/dev/null 2>&1; then
    echo "ERROR: 'prime-agent' not found on PATH." >&2
    echo "Install/authenticate the CLI, then re-verify its flags (this scaffold" >&2
    echo "targets -p, --mode json, --autonomous[-gate*], --fork, --model per" >&2
    echo "PrimeIntellect-ai/prime-agent's usage.md) before running at scale." >&2
    exit 1
  fi
  if [[ -z "$PRIME_AGENT_MODEL" ]]; then
    echo "ERROR: PRIME_AGENT_MODEL is not set." >&2
    echo "Run 'prime-agent model list' to find a pattern, then:" >&2
    echo "  export PRIME_AGENT_MODEL=\"provider/model-id\"" >&2
    echo "Use the identical string for both conditions -- model choice must not be a confound." >&2
    exit 1
  fi
}

record_meta() {
  # $1: meta_json path, $2: condition ('a'|'b'), $3: task_id, $4: start_ts,
  # $5: end_ts, $6: wall_time_s, $7: exit_code, $8: session_id (may be empty),
  # $9: checker_cmd, $10: workdir
  python3 - "$@" <<'PYEOF'
import json
import sys

(meta_path, condition, task_id, start_ts, end_ts, wall_time_s,
 exit_code, session_id, checker_cmd, workdir) = sys.argv[1:11]

json.dump({
    "task_id": int(task_id),
    "condition": condition,
    "model": PRIME_AGENT_MODEL if (PRIME_AGENT_MODEL := __import__("os").environ.get("PRIME_AGENT_MODEL", "")) else "",
    "start_ts": float(start_ts),
    "end_ts": float(end_ts),
    "wall_time_s": float(wall_time_s),
    "exit_code": int(exit_code),
    "session_id": session_id,
    "checker_cmd": checker_cmd,
    "workdir": workdir,
}, open(meta_path, "w"), indent=2)
PYEOF
}

extract_session_id() {
  # $1: path to a --mode json transcript -- prints the session id from the
  # header `session` event, or an empty string if not found/parseable.
  python3 - "$1" <<'PYEOF'
import json
import sys

path = sys.argv[1]
session_id = ""
try:
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            if evt.get("type") == "session" and evt.get("id"):
                session_id = evt["id"]
                break
except FileNotFoundError:
    pass
print(session_id)
PYEOF
}
