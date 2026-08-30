def apply_discount(price, discount_rate):
    """Apply a percentage discount to a price and return the discounted price."""
    discount_amount = price * discount_rate
    discounted_price = price - discount_amount
    return discount_amount
