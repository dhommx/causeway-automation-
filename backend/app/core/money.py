"""Money helpers. All amounts are Decimal, never float. BHD has 3 decimal places."""

from decimal import ROUND_HALF_UP, Decimal

BHD_PLACES = Decimal("0.001")


def to_decimal(value: object) -> Decimal:
    """Convert a cell value to Decimal without picking up float noise (8.636 stays 8.636)."""
    if value is None or value == "":
        return Decimal(0)
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(repr(value))
    return Decimal(str(value).replace(",", "").strip())


def money(value: object, places: Decimal = BHD_PLACES) -> Decimal:
    """Round to the currency's places, half up (0.0005 -> 0.001), the way accountants round."""
    return to_decimal(value).quantize(places, rounding=ROUND_HALF_UP)


def percent_of(amount: object, rate_percent: object) -> Decimal:
    """rate_percent is written as on paper: 2.2 means 2.2%."""
    return money(to_decimal(amount) * to_decimal(rate_percent) / Decimal(100))


def fmt(value: object) -> str:
    """Fixed 3-decimal text for display and JSON (keeps trailing zeros: 158.000)."""
    return f"{money(value):.3f}"
