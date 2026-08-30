import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task08_buggy", Path(__file__).parent / "08_buggy.py")
task08_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task08_buggy)

globals().update({k: v for k, v in vars(task08_buggy).items() if not k.startswith('_')})

def test_vowel_count_prefix_full_word():
    assert vowel_count_prefix("hello", 5) == 2


def test_vowel_count_prefix_no_vowels():
    assert vowel_count_prefix("rhythm", 6) == 0
