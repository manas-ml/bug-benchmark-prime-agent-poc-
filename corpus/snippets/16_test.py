import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task16_buggy", Path(__file__).parent / "16_buggy.py")
task16_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task16_buggy)

globals().update({k: v for k, v in vars(task16_buggy).items() if not k.startswith('_')})

def test_is_within_budget_at_boundary():
    assert is_within_budget(100, 100) is True


def test_is_within_budget_over():
    assert is_within_budget(150, 100) is False
