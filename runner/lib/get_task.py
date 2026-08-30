#!/usr/bin/env python3
"""Print one task record from corpus/tasks.jsonl as `export KEY=value` shell statements."""
import json
import shlex
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKS_PATH = REPO_ROOT / "corpus" / "tasks.jsonl"

EXPORTED_FIELDS = ("snippet_path", "test_path", "bug_type", "bug_line", "checker_cmd")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: get_task.py <task_id>")
    task_id = int(sys.argv[1])
    for line in TASKS_PATH.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record["id"] == task_id:
            for key in EXPORTED_FIELDS:
                print(f"export TASK_{key.upper()}={shlex.quote(str(record[key]))}")
            return
    sys.exit(f"task id {task_id} not found in {TASKS_PATH}")


if __name__ == "__main__":
    main()
