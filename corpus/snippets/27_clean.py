def unique_visitors(session_id, seen=None):
    """Track and return the list of unique session_ids seen so far."""
    if seen is None:
        seen = []
    if session_id not in seen:
        seen.append(session_id)
    return seen
