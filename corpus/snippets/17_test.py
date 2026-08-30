import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task17_buggy", Path(__file__).parent / "17_buggy.py")
task17_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task17_buggy)

globals().update({k: v for k, v in vars(task17_buggy).items() if not k.startswith('_')})

from types import SimpleNamespace


def test_discounted_price_without_coupon():
    assert discounted_price(100) == 100


def test_discounted_price_with_coupon():
    coupon = SimpleNamespace(amount=15)
    assert discounted_price(100, coupon) == 85
