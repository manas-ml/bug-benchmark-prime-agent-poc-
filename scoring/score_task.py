#!/usr/bin/env python3
"""Score a single task's run against its ground truth.

Reads three things per (task, condition):
  - the task's ground-truth record from corpus/tasks.jsonl
  - the run's `--mode json` transcript (results/condition_X/task_NN.json)
  - the run's sidecar metadata (results/condition_X/task_NN.meta.json), written
    by the runner scripts with wall-clock timing and the preserved workdir path

`found` is determined authoritatively by re-running the task's checker against
the on-disk result of the run (the workdir the runner preserved), not by
trying to infer pass/fail from the transcript. The reported line/bug/fix are
parsed from the transcript's final assistant message.

Known limitation: prime-agent's `--mode json` schema (as documented in
packages/coding-agent/docs/json.md at the time this was written) does not
define a `usage`/token-count event. `tokens_used` is therefore extracted
best-effort by scanning every event for token-count-looking fields; treat it
as approximate and re-verify against the live JSON schema before trusting it
at scale. `wall_time_s` is NOT taken from the transcript -- it comes from the
runner's own sidecar timing, which is authoritative.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]

FINAL_ANSWER_RE = re.compile(
    r"FINAL_ANSWER:\s*line\s*=\s*(?P<line>\d+)\s*,\s*bug\s*=\s*(?P<bug>[^,]*?)\s*,\s*fix\s*=\s*(?P<fix>.*)",
    re.IGNORECASE,
)
# Heuristic: any other "line <N>" mention in the agent's own prose, used only
# to estimate false_positives (other lines it called out as buggy).
LINE_MENTION_RE = re.compile(r"\bline\s+(\d+)\b", re.IGNORECASE)


def load_task(task_id: int, tasks_path: Path = REPO_ROOT / "corpus" / "tasks.jsonl") -> dict:
    for line in tasks_path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record["id"] == task_id:
            return record
    raise ValueError(f"task id {task_id} not found in {tasks_path}")


def read_jsonl_events(transcript_path: Path) -> list[dict]:
    events = []
    if not transcript_path.exists():
        return events
    for line in transcript_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def extract_final_text(events: list[dict]) -> str:
    """Concatenate assistant text from `message_end` events, per json.md's own
    documented jq pattern (`select(.type == "message_end")`)."""
    chunks = []
    for evt in events:
        if evt.get("type") != "message_end":
            continue
        message = evt.get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            chunks.append(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    chunks.append(part["text"])
    return "\n".join(chunks)


def extract_tokens_used(events: list[dict]) -> Optional[int]:
    """Best-effort: no documented usage event exists (see module docstring).
    Scan every event dict recursively for a key matching /token/i and take the
    largest single value seen, on the assumption a cumulative/session-total
    field (if present at all) will be the largest such number."""
    best: Optional[int] = None

    def walk(obj: Any) -> None:
        nonlocal best
        if isinstance(obj, dict):
            for key, value in obj.items():
                if "token" in key.lower() and isinstance(value, (int, float)):
                    if best is None or value > best:
                        best = int(value)
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    for evt in events:
        walk(evt)
    return best


def run_checker(checker_cmd: str, cwd: Path) -> bool:
    result = subprocess.run(
        checker_cmd, shell=True, cwd=str(cwd),
        capture_output=True, text=True,
    )
    return result.returncode == 0


def score_task(task: dict, transcript_path: Path, meta_path: Path) -> dict:
    events = read_jsonl_events(transcript_path)
    final_text = extract_final_text(events)

    match = FINAL_ANSWER_RE.search(final_text)
    reported_line: Optional[int] = int(match.group("line")) if match else None

    bug_line = task["bug_line"]
    correct_location = reported_line == bug_line
    within_one = reported_line is not None and abs(reported_line - bug_line) <= 1

    other_lines = set()
    if match:
        rest = final_text[: match.start()] + final_text[match.end():]
    else:
        rest = final_text
    for m in LINE_MENTION_RE.finditer(rest):
        n = int(m.group(1))
        if n != bug_line:
            other_lines.add(n)
    false_positives = len(other_lines)

    meta: dict = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
    wall_time_s = meta.get("wall_time_s")
    workdir = meta.get("workdir")
    checker_cmd_from_meta = meta.get("checker_cmd") or task["checker_cmd"]

    checker_passed = False
    if workdir and Path(workdir).exists():
        checker_passed = run_checker(checker_cmd_from_meta, Path(workdir))

    found = checker_passed and within_one

    return {
        "task_id": task["id"],
        "bug_type": task["bug_type"],
        "found": found,
        "correct_location": correct_location,
        "false_positives": false_positives,
        "tokens_used": extract_tokens_used(events),
        "wall_time_s": wall_time_s,
        "checker_passed": checker_passed,
        "reported_line": reported_line,
        "bug_line": bug_line,
        "exit_code": meta.get("exit_code"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--condition", choices=["a", "b"], required=True)
    parser.add_argument("--results-dir", type=Path, default=None,
                         help="defaults to results/condition_<a|b>/")
    args = parser.parse_args()

    results_dir = args.results_dir or (REPO_ROOT / "results" / f"condition_{args.condition}")
    stem = f"{args.task_id:02d}"
    transcript_path = results_dir / f"task_{stem}.json"
    meta_path = results_dir / f"task_{stem}.meta.json"

    task = load_task(args.task_id)
    result = score_task(task, transcript_path, meta_path)
    result["condition"] = args.condition
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
