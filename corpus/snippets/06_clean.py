def add_item_to_cart(item, cart=None):
    """Add an item to a shopping cart list, creating a new cart if none is given."""
    if cart is None:
        cart = []
    cart.append(item)
    return cart
