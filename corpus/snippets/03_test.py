import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task03_buggy", Path(__file__).parent / "03_buggy.py")
task03_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task03_buggy)

globals().update({k: v for k, v in vars(task03_buggy).items() if not k.startswith('_')})

def test_format_full_name_without_middle():
    assert format_full_name("Ada", "Lovelace") == "Ada Lovelace"


def test_format_full_name_with_middle():
    assert format_full_name("Ada", "Lovelace", " Marie ") == "Ada Marie Lovelace"
