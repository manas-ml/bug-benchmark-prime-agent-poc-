import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task18_buggy", Path(__file__).parent / "18_buggy.py")
task18_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task18_buggy)

globals().update({k: v for k, v in vars(task18_buggy).items() if not k.startswith('_')})

def test_normalize_score_basic():
    assert normalize_score(50, 200) == 25.0


def test_normalize_score_full_marks():
    assert normalize_score(80, 80) == 100.0
