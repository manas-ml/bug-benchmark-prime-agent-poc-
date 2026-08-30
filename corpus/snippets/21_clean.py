def recent_top_scores(scores):
    """Return the top 3 highest scores from the given scores list."""
    return sorted(scores, reverse=True)[:3]
