import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task15_buggy", Path(__file__).parent / "15_buggy.py")
task15_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task15_buggy)

globals().update({k: v for k, v in vars(task15_buggy).items() if not k.startswith('_')})

def test_reverse_prefix_basic():
    assert reverse_prefix("abcdef", 4) == "dcba"


def test_reverse_prefix_whole_string():
    assert reverse_prefix("hi", 2) == "ih"
