def increment_counter(key, counters={}):
    """Increment the count for `key` in a counters dict, creating a new dict if none is given."""
    if counters is None:
        counters = {}
    counters[key] = counters.get(key, 0) + 1
    return counters
