#!/usr/bin/env python3
"""Roll every task+condition's score into one CSV for analysis.

Columns: task_index,condition,found,correct_location,false_positives,tokens_used,wall_time_s

`task_index` is the task's 0-based position in the shared shuffled order
(corpus/task_order.json), not its raw corpus id -- the whole point of the
analysis is "does the curve move over the course of the run," which only
makes sense against execution order.

Missing runs (no transcript/meta file yet, e.g. mid-pilot) are skipped with a
warning to stderr rather than emitting a row with fabricated data, so
"aggregate.py produces a clean CSV with no missing rows" holds for whatever
subset has actually been run.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_task import load_task, score_task  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ["task_index", "condition", "found", "correct_location", "false_positives", "tokens_used", "wall_time_s"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "results" / "aggregate.csv")
    parser.add_argument("--tasks-jsonl", type=Path, default=REPO_ROOT / "corpus" / "tasks.jsonl")
    parser.add_argument("--task-order", type=Path, default=REPO_ROOT / "corpus" / "task_order.json")
    parser.add_argument("--results-root", type=Path, default=REPO_ROOT / "results")
    args = parser.parse_args()

    order = json.loads(args.task_order.read_text())["order"]
    rows = []
    skipped = 0

    for task_index, task_id in enumerate(order):
        task = load_task(task_id, args.tasks_jsonl)
        for condition in ("a", "b"):
            results_dir = args.results_root / f"condition_{condition}"
            stem = f"{task_id:02d}"
            transcript_path = results_dir / f"task_{stem}.json"
            meta_path = results_dir / f"task_{stem}.meta.json"
            if not transcript_path.exists() or not meta_path.exists():
                print(f"skipping task {task_id} condition {condition}: no run found "
                      f"(expected {transcript_path.name} + {meta_path.name})", file=sys.stderr)
                skipped += 1
                continue
            result = score_task(task, transcript_path, meta_path)
            rows.append({
                "task_index": task_index,
                "condition": condition,
                "found": int(result["found"]),
                "correct_location": int(result["correct_location"]),
                "false_positives": result["false_positives"],
                "tokens_used": result["tokens_used"] if result["tokens_used"] is not None else "",
                "wall_time_s": result["wall_time_s"] if result["wall_time_s"] is not None else "",
            })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows ({skipped} task/condition pairs skipped, no run found) -> {args.out}")


if __name__ == "__main__":
    main()
