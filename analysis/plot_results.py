#!/usr/bin/env python3
"""Plot rolling accuracy/cost curves from results/aggregate.csv and print the
first-10-vs-last-10 headline summary.

Produces two overlay charts (Condition A vs Condition B, by task_index):
  - results/found_rate_rolling.png     rolling mean of `found` (window=5)
  - results/cost_rolling.png           rolling mean of tokens_used and wall_time_s (window=5)

And prints, per condition and metric, the mean over the first 10 vs. last 10
tasks (by task_index) -- the headline number for whether a curve actually
moved over the course of the run.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOW = 5

CONDITION_LABELS = {"a": "Condition A (continuous)", "b": "Condition B (baseline)"}
CONDITION_COLORS = {"a": "#2f6fed", "b": "#e0663e"}


def rolling_by_condition(df: pd.DataFrame, metric: str) -> dict[str, pd.Series]:
    out = {}
    for condition, group in df.groupby("condition"):
        series = group.sort_values("task_index").set_index("task_index")[metric]
        out[condition] = series.rolling(window=WINDOW, min_periods=1).mean()
    return out


def plot_metric(df: pd.DataFrame, metric: str, ylabel: str, title: str, out_path: Path) -> None:
    rolling = rolling_by_condition(df, metric)
    fig, ax = plt.subplots(figsize=(9, 5))
    for condition in ("a", "b"):
        if condition not in rolling:
            continue
        series = rolling[condition]
        ax.plot(series.index, series.values, label=CONDITION_LABELS[condition],
                 color=CONDITION_COLORS[condition], linewidth=2)
    ax.set_xlabel("task index (shared shuffled order)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"wrote {out_path}")


def print_headline_summary(df: pd.DataFrame, metrics: list[str]) -> None:
    print("\n=== First-10 vs last-10 summary (by task_index) ===")
    for condition in ("a", "b"):
        sub = df[df["condition"] == condition].sort_values("task_index")
        if sub.empty:
            print(f"\n{CONDITION_LABELS[condition]}: no data")
            continue
        n = len(sub)
        first10 = sub.head(min(10, n))
        last10 = sub.tail(min(10, n))
        print(f"\n{CONDITION_LABELS[condition]} ({n} tasks scored):")
        for metric in metrics:
            first_mean = first10[metric].mean()
            last_mean = last10[metric].mean()
            delta = last_mean - first_mean
            print(f"  {metric:<16s} first10={first_mean:8.3f}  last10={last_mean:8.3f}  delta={delta:+.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=REPO_ROOT / "results" / "aggregate.csv")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "results")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    if df.empty:
        raise SystemExit(f"{args.csv} has no rows -- run the corpus/runners/aggregate.py pipeline first")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    plot_metric(df, "found", "rolling mean of `found` (window=5)",
                "Accuracy curve: found rate vs. task index", args.out_dir / "found_rate_rolling.png")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    for ax, metric, ylabel in ((ax1, "tokens_used", "rolling mean tokens_used"),
                                (ax2, "wall_time_s", "rolling mean wall_time_s")):
        rolling = rolling_by_condition(df, metric)
        for condition in ("a", "b"):
            if condition not in rolling:
                continue
            series = rolling[condition]
            ax.plot(series.index, series.values, label=CONDITION_LABELS[condition],
                     color=CONDITION_COLORS[condition], linewidth=2)
        ax.set_xlabel("task index (shared shuffled order)")
        ax.set_ylabel(ylabel)
        ax.legend()
        ax.grid(alpha=0.3)
    fig.suptitle("Cost curves: tokens & wall time vs. task index")
    fig.tight_layout()
    cost_path = args.out_dir / "cost_rolling.png"
    fig.savefig(cost_path, dpi=150)
    plt.close(fig)
    print(f"wrote {cost_path}")

    print_headline_summary(df, ["found", "correct_location", "false_positives", "tokens_used", "wall_time_s"])


if __name__ == "__main__":
    main()
