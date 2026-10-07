from decimal import Decimal

import pytest

from quote_calculator import Quote, calculate_quote


def test_regular_quote_returns_itemized_amounts() -> None:
    quote = calculate_quote(Decimal("12.50"), 3, Decimal("0.08"))

    assert isinstance(quote, Quote)
    assert quote.subtotal == Decimal("37.50")
    assert quote.discount == Decimal("0.00")
    assert quote.total == quote.subtotal - quote.discount + quote.tax


def test_volume_order_receives_discount() -> None:
    quote = calculate_quote(Decimal("8.00"), 10, Decimal("0.05"))

    assert quote.discount > Decimal("0")
    assert quote.total < quote.subtotal + quote.tax


def test_tax_is_included_in_total() -> None:
    quote = calculate_quote(Decimal("20.00"), 12, Decimal("0.075"))

    assert quote.tax > Decimal("0")
    assert quote.total == quote.subtotal - quote.discount + quote.tax


def test_amounts_have_cent_precision() -> None:
    quote = calculate_quote(Decimal("1.005"), 1, Decimal("0.0825"))

    for amount in (quote.subtotal, quote.discount, quote.tax, quote.total):
        assert amount.as_tuple().exponent == -2


@pytest.mark.parametrize(
    ("unit_price", "quantity", "tax_rate"),
    [
        (Decimal("-0.01"), 1, Decimal("0.05")),
        (Decimal("1.00"), 0, Decimal("0.05")),
        (Decimal("1.00"), 1, Decimal("1.01")),
        (Decimal("1.00"), 1, Decimal("-0.01")),
    ],
)
def test_invalid_inputs_are_rejected(
    unit_price: Decimal, quantity: int, tax_rate: Decimal
) -> None:
    with pytest.raises(ValueError):
        calculate_quote(unit_price, quantity, tax_rate)
