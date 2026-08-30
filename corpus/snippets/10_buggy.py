def total_extra_items(base_items, extra_items=None):
    """Return the combined count of base_items plus any extra_items provided."""
    count = len(base_items)
    count += len(extra_items)
    return count
