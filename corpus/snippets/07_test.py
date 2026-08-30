import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task07_buggy", Path(__file__).parent / "07_buggy.py")
task07_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task07_buggy)

globals().update({k: v for k, v in vars(task07_buggy).items() if not k.startswith('_')})

def test_strip_outer_chars_basic():
    assert strip_outer_chars("[hello]") == "hello"


def test_strip_outer_chars_quotes():
    assert strip_outer_chars('"hi"') == "hi"
