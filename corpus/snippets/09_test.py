import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task09_buggy", Path(__file__).parent / "09_buggy.py")
task09_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task09_buggy)

globals().update({k: v for k, v in vars(task09_buggy).items() if not k.startswith('_')})

def test_is_below_freezing_at_boundary():
    assert is_below_freezing(0) is False


def test_is_below_freezing_negative():
    assert is_below_freezing(-5) is True
