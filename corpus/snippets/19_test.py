import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task19_buggy", Path(__file__).parent / "19_buggy.py")
task19_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task19_buggy)

globals().update({k: v for k, v in vars(task19_buggy).items() if not k.startswith('_')})

def test_total_price_display_basic():
    assert total_price_display(1050) == "$10.5"


def test_total_price_display_whole_dollars():
    assert total_price_display(500) == "$5.0"
