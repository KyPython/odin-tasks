"""Itemized quote calculations using decimal arithmetic."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

_CENT = Decimal("0.01")
_VOLUME_THRESHOLD = 10
_VOLUME_DISCOUNT_RATE = Decimal("0.10")


@dataclass(frozen=True)
class Quote:
    """The monetary components of a calculated quote."""

    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def calculate_quote(
    unit_price: Decimal, quantity: int, tax_rate: Decimal
) -> Quote:
    """Calculate an itemized quote after validating all inputs."""
    if unit_price < 0:
        raise ValueError("unit_price must be non-negative")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("quantity must be a positive integer")
    if tax_rate < 0 or tax_rate > 1:
        raise ValueError("tax_rate must be between zero and one")

    subtotal = unit_price * quantity
    discount = (
        subtotal * _VOLUME_DISCOUNT_RATE
        if quantity >= _VOLUME_THRESHOLD
        else Decimal("0")
    )
    tax = subtotal * tax_rate

    return Quote(
        subtotal=_money(subtotal),
        discount=_money(discount),
        tax=_money(tax),
        total=_money(subtotal - discount + tax),
    )

