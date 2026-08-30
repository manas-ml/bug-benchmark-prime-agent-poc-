import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task29_buggy", Path(__file__).parent / "29_buggy.py")
task29_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task29_buggy)

globals().update({k: v for k, v in vars(task29_buggy).items() if not k.startswith('_')})

def test_multiples_of_k_up_to_inclusive_boundary():
    assert multiples_of_k_up_to(9, 3) == 3


def test_multiples_of_k_up_to_no_multiples():
    assert multiples_of_k_up_to(5, 7) == 0
