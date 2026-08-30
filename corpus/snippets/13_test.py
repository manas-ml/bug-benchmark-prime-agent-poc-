import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task13_buggy", Path(__file__).parent / "13_buggy.py")
task13_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task13_buggy)

globals().update({k: v for k, v in vars(task13_buggy).items() if not k.startswith('_')})

def test_increment_counter_basic():
    assert increment_counter("a") == {"a": 1}


def test_increment_counter_independent_calls():
    increment_counter("a")
    assert increment_counter("b") == {"b": 1}
