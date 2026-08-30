import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task10_buggy", Path(__file__).parent / "10_buggy.py")
task10_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task10_buggy)

globals().update({k: v for k, v in vars(task10_buggy).items() if not k.startswith('_')})

def test_total_extra_items_without_extra():
    assert total_extra_items(["a", "b"]) == 2


def test_total_extra_items_with_extra():
    assert total_extra_items(["a", "b"], ["c", "d", "e"]) == 5
