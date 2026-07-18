from decimal import Decimal


def calculate_total(unit_price: Decimal, quantity: int) -> Decimal:
    """Calculate the total price for a quantity of products."""

    if unit_price < Decimal("0"):
        raise ValueError("Unit price cannot be negative.")

    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")

    return unit_price * quantity