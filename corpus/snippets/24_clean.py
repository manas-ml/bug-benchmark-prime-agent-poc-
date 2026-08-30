def merge_tags(existing_tags, new_tags=None):
    """Merge new_tags into existing_tags, avoiding duplicates, if new_tags is given."""
    merged = list(existing_tags)
    if new_tags is not None:
        for tag in new_tags:
            if tag not in merged:
                merged.append(tag)
    return merged
