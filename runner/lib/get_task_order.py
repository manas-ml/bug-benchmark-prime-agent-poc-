#!/usr/bin/env python3
"""Print the shared shuffled task order (space-separated task ids), optionally truncated.

Both conditions must iterate tasks in this same order (a difference in ordering is
itself a confound) -- see corpus/task_order.json, written once by generate_corpus.py.
"""
import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ORDER_PATH = REPO_ROOT / "corpus" / "task_order.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="only print the first N ids")
    args = parser.parse_args()

    order = json.loads(ORDER_PATH.read_text())["order"]
    if args.limit is not None:
        order = order[: args.limit]
    print(" ".join(str(i) for i in order))


if __name__ == "__main__":
    main()
