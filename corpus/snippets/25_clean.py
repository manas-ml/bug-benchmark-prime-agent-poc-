def full_address(street, city, zip_code):
    """Build a formatted one-line mailing address string."""
    partial_address = f"{street}, {city}"
    complete_address = f"{partial_address} {zip_code}"
    return complete_address
