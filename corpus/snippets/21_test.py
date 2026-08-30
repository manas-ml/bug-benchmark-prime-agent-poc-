import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task21_buggy", Path(__file__).parent / "21_buggy.py")
task21_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task21_buggy)

globals().update({k: v for k, v in vars(task21_buggy).items() if not k.startswith('_')})

def test_recent_top_scores_basic():
    assert recent_top_scores([50, 90, 10, 70, 30]) == [90, 70, 50]


def test_recent_top_scores_few_scores():
    assert recent_top_scores([5, 1]) == [5, 1]
