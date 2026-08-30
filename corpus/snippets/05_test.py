import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task05_buggy", Path(__file__).parent / "05_buggy.py")
task05_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task05_buggy)

globals().update({k: v for k, v in vars(task05_buggy).items() if not k.startswith('_')})

def test_format_countdown_basic():
    assert format_countdown(5) == "T-minus 5"


def test_format_countdown_zero():
    assert format_countdown(0) == "T-minus 0"
