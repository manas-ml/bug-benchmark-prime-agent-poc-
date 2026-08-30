def normalize_score(raw_score, max_score):
    """Scale raw_score to a 0-100 range given the maximum possible score."""
    ratio = raw_score / max_score
    percentage = ratio * 100
    return ratio
