import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task22_buggy", Path(__file__).parent / "22_buggy.py")
task22_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task22_buggy)

globals().update({k: v for k, v in vars(task22_buggy).items() if not k.startswith('_')})

def test_count_positive_in_first_n_basic():
    assert count_positive_in_first_n([1, -2, 3, -4, 5], 5) == 3


def test_count_positive_in_first_n_prefix():
    assert count_positive_in_first_n([1, 2, -3, 4], 2) == 2
