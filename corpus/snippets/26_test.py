import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task26_buggy", Path(__file__).parent / "26_buggy.py")
task26_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task26_buggy)

globals().update({k: v for k, v in vars(task26_buggy).items() if not k.startswith('_')})

def test_average_age_label_basic():
    assert average_age_label([10, 20, 30]) == "Average age: 20"


def test_average_age_label_single():
    assert average_age_label([25]) == "Average age: 25"
