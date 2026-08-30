import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task02_buggy", Path(__file__).parent / "02_buggy.py")
task02_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task02_buggy)

globals().update({k: v for k, v in vars(task02_buggy).items() if not k.startswith('_')})

def test_is_eligible_voter_at_boundary():
    assert is_eligible_voter(18) is True


def test_is_eligible_voter_below_boundary():
    assert is_eligible_voter(17) is False
