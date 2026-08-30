import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task01_buggy", Path(__file__).parent / "01_buggy.py")
task01_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task01_buggy)

globals().update({k: v for k, v in vars(task01_buggy).items() if not k.startswith('_')})

def test_sum_first_n_partial():
    assert sum_first_n([1, 2, 3, 4], 3) == 6


def test_sum_first_n_full_list():
    assert sum_first_n([5, 5, 5], 3) == 15
