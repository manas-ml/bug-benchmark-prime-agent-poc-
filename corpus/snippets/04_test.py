import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task04_buggy", Path(__file__).parent / "04_buggy.py")
task04_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task04_buggy)

globals().update({k: v for k, v in vars(task04_buggy).items() if not k.startswith('_')})

def test_average_basic():
    assert average([2, 4, 6]) == 4.0


def test_average_single_value():
    assert average([10]) == 10.0
