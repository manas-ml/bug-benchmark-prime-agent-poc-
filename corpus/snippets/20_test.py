import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("task20_buggy", Path(__file__).parent / "20_buggy.py")
task20_buggy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task20_buggy)

globals().update({k: v for k, v in vars(task20_buggy).items() if not k.startswith('_')})

def test_tag_document_basic():
    assert tag_document("doc1") == {"doc_id": "doc1", "tags": ["reviewed"]}


def test_tag_document_independent_calls():
    tag_document("doc1")
    result = tag_document("doc2")
    assert result["tags"] == ["reviewed"]
