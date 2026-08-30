import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task14_buggy", Path(__file__).parent / "14_buggy.py")
task14_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task14_buggy)

globals().update({k: v for k, v in vars(task14_buggy).items() if not k.startswith('_')})

def test_drop_header_rows_basic():
    assert drop_header_rows(["h1", "h2", "d1", "d2"]) == ["d1", "d2"]


def test_drop_header_rows_extra_data():
    assert drop_header_rows(["h1", "h2", "d1", "d2", "d3"]) == ["d1", "d2", "d3"]
