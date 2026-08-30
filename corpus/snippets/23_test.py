import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task23_buggy", Path(__file__).parent / "23_buggy.py")
task23_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task23_buggy)

globals().update({k: v for k, v in vars(task23_buggy).items() if not k.startswith('_')})

def test_exceeds_speed_limit_at_boundary():
    assert exceeds_speed_limit(60, 60) is False


def test_exceeds_speed_limit_over():
    assert exceeds_speed_limit(65, 60) is True
