from decimal import Decimal

from app.core.money import fmt, money, percent_of, to_decimal


def test_float_noise_is_removed():
    assert to_decimal(8.636) == Decimal("8.636")
    assert money(17 * to_decimal(8.636)) == Decimal("146.812")


def test_rounding_is_half_up_to_three_places():
    assert money("3.5475") == Decimal("3.548")
    assert money("2.0024") == Decimal("2.002")


def test_percent_of():
    assert percent_of(91, "2.2") == Decimal("2.002")
    assert percent_of(215, "1.65") == Decimal("3.548")


def test_fmt_keeps_trailing_zeros():
    assert fmt(158) == "158.000"
    assert to_decimal("1,234.5") == Decimal("1234.5")
