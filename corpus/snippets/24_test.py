import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task24_buggy", Path(__file__).parent / "24_buggy.py")
task24_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task24_buggy)

globals().update({k: v for k, v in vars(task24_buggy).items() if not k.startswith('_')})

def test_merge_tags_without_new_tags():
    assert merge_tags(["a", "b"]) == ["a", "b"]


def test_merge_tags_with_new_tags():
    assert merge_tags(["a"], ["b", "a"]) == ["a", "b"]
