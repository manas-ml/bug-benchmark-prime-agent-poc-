def total_price_display(cents):
    """Convert a price in cents (int) to a dollar-formatted string, e.g. 1050 -> '$10.5'."""
    dollars = cents / 100
    return "$" + round(dollars, 2)
