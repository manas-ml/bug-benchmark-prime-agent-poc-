import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task06_buggy", Path(__file__).parent / "06_buggy.py")
task06_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task06_buggy)

globals().update({k: v for k, v in vars(task06_buggy).items() if not k.startswith('_')})

def test_add_item_to_cart_basic():
    assert add_item_to_cart("apple") == ["apple"]


def test_add_item_to_cart_independent_calls():
    add_item_to_cart("apple")
    assert add_item_to_cart("banana") == ["banana"]
