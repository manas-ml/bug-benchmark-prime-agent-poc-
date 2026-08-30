import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task30_buggy", Path(__file__).parent / "30_buggy.py")
task30_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task30_buggy)

globals().update({k: v for k, v in vars(task30_buggy).items() if not k.startswith('_')})

def test_passwords_differ_when_matching():
    assert passwords_differ("secret", "secret") is False


def test_passwords_differ_when_mismatched():
    assert passwords_differ("secret", "wrong") is True
