def discounted_price(price, coupon=None):
    """Apply a coupon's discount to price if a coupon is provided."""
    final_price = price
    final_price = price - coupon.amount
    return round(final_price, 2)
