# Quote calculation behavior

`calculate_quote(unit_price, quantity, tax_rate)` returns a `Quote` with the
following monetary amounts:

1. `subtotal` is `unit_price * quantity`.
2. Orders of 10 or more units receive a 10% volume discount; smaller orders
   receive no discount.
3. `tax` is calculated from the discounted amount:
   `(subtotal - discount) * tax_rate`.
4. `total` is `subtotal - discount + tax`.
5. Every returned monetary amount is rounded to two decimal places using
   conventional half-up rounding.

Inputs use `Decimal` values for `unit_price` and `tax_rate`. The unit price
must be non-negative, quantity must be a positive integer, and tax rate must
be between zero and one inclusive. Invalid inputs raise `ValueError`.

