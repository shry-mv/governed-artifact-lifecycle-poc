from decimal import Decimal

import pytest

from pricing_app.calculator import calculate_total


def test_calculate_total() -> None:
    result = calculate_total(Decimal("100.50"), 2)

    assert result == Decimal("201.00")


def test_rejects_negative_price() -> None:
    with pytest.raises(ValueError, match="Unit price cannot be negative"):
        calculate_total(Decimal("-10.00"), 2)


def test_rejects_zero_quantity() -> None:
    with pytest.raises(ValueError, match="Quantity must be at least 1"):
        calculate_total(Decimal("100.00"), 0)