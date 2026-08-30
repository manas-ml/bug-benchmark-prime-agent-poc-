import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task12_buggy", Path(__file__).parent / "12_buggy.py")
task12_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task12_buggy)

globals().update({k: v for k, v in vars(task12_buggy).items() if not k.startswith('_')})

def test_parse_quantity_basic():
    assert parse_quantity(" 42 ") == 42


def test_parse_quantity_arithmetic():
    assert parse_quantity("4") + 1 == 5
