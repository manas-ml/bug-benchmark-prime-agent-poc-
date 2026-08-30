import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task11_buggy", Path(__file__).parent / "11_buggy.py")
task11_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task11_buggy)

globals().update({k: v for k, v in vars(task11_buggy).items() if not k.startswith('_')})

def test_apply_discount_basic():
    assert apply_discount(100, 0.2) == 80


def test_apply_discount_no_discount():
    assert apply_discount(50, 0.0) == 50
