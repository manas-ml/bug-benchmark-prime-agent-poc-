import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task28_buggy", Path(__file__).parent / "28_buggy.py")
task28_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task28_buggy)

globals().update({k: v for k, v in vars(task28_buggy).items() if not k.startswith('_')})

def test_skip_first_and_last_pair_basic():
    assert skip_first_and_last_pair([1, 2, 3, 4, 5, 6, 7, 8]) == [3, 4, 5, 6]


def test_skip_first_and_last_pair_min_size():
    assert skip_first_and_last_pair([1, 2, 3, 4, 5]) == [3]
