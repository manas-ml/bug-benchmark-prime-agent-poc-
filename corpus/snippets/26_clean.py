def average_age_label(ages):
    """Compute the rounded average age and return it as a whole-number string label."""
    avg = sum(ages) / len(ages)
    rounded = round(avg)
    return "Average age: " + str(rounded)
