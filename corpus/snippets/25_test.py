import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task25_buggy", Path(__file__).parent / "25_buggy.py")
task25_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task25_buggy)

globals().update({k: v for k, v in vars(task25_buggy).items() if not k.startswith('_')})

def test_full_address_basic():
    assert full_address("1 Main St", "Springfield", "12345") == "1 Main St, Springfield 12345"


def test_full_address_other_city():
    assert full_address("42 Oak Ave", "Metropolis", "99999") == "42 Oak Ave, Metropolis 99999"
