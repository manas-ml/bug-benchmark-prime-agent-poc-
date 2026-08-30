def tag_document(doc_id, tags=None):
    """Return a dict mapping doc_id to a list of tags, using a fresh list by default."""
    if tags is None:
        tags = []
    tags.append("reviewed")
    return {"doc_id": doc_id, "tags": tags}
