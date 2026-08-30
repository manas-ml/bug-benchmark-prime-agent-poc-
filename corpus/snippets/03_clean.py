def format_full_name(first, last, middle=None):
    """Combine first, optional middle, and last names into one string."""
    parts = [first]
    if middle is not None:
        parts.append(middle.strip())
    parts.append(last)
    return " ".join(parts)
