import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task27_buggy", Path(__file__).parent / "27_buggy.py")
task27_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task27_buggy)

globals().update({k: v for k, v in vars(task27_buggy).items() if not k.startswith('_')})

def test_unique_visitors_basic():
    assert unique_visitors("s1") == ["s1"]


def test_unique_visitors_independent_calls():
    unique_visitors("s1")
    assert unique_visitors("s2") == ["s2"]
