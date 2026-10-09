from decimal import ROUND_HALF_UP, Decimal, localcontext

import pytest

from app.money import decimal_to_scaled, scaled_to_decimal


def test_scaled_usd_cents() -> None:
    assert scaled_to_decimal("12000050", 2) == Decimal("120000.50")
    assert type(scaled_to_decimal("12000050", 2)) is Decimal


def test_jpy_scale_zero_divides_by_one() -> None:
    assert scaled_to_decimal("8000000", 0) == Decimal("8000000")
    assert scaled_to_decimal("149", 0) == Decimal("149") / Decimal(1)


def test_rejects_decimal_point_and_exponent() -> None:
    with pytest.raises(ValueError):
        scaled_to_decimal("12.00", 2)
    with pytest.raises(ValueError):
        scaled_to_decimal("1e5", 0)
    with pytest.raises(ValueError):
        scaled_to_decimal("", 0)


@pytest.mark.parametrize("scaled", ["12.00", "1e5", "1E5", "+100", " 100", "100 ", "--1"])
def test_rejects_non_digit_strings(scaled: str) -> None:
    with pytest.raises(ValueError):
        scaled_to_decimal(scaled, 0)


def test_half_even_round_trip() -> None:
    assert decimal_to_scaled(Decimal("1.005"), 2) == "100"
    assert decimal_to_scaled(Decimal("1.015"), 2) == "102"
    assert decimal_to_scaled(Decimal("2.5"), 0) == "2"
    assert decimal_to_scaled(Decimal("-1.5"), 0) == "-2"
    assert decimal_to_scaled(Decimal("-2.5"), 0) == "-2"

    assert decimal_to_scaled(scaled_to_decimal("12000050", 2), 2) == "12000050"
    assert scaled_to_decimal(decimal_to_scaled(Decimal("120000.50"), 2), 2) == Decimal(
        "120000.50"
    )
    assert decimal_to_scaled(scaled_to_decimal("8000000", 0), 0) == "8000000"
    assert decimal_to_scaled(scaled_to_decimal("-12000050", 2), 2) == "-12000050"

    with localcontext() as ctx:
        ctx.rounding = ROUND_HALF_UP
        assert decimal_to_scaled(Decimal("1.005"), 2) == "100"
        assert decimal_to_scaled(Decimal("1.015"), 2) == "102"


def test_int64_bounds() -> None:
    minimum = "-9223372036854775808"
    maximum = "9223372036854775807"
    assert decimal_to_scaled(scaled_to_decimal(minimum, 0), 0) == minimum
    assert decimal_to_scaled(scaled_to_decimal(maximum, 0), 0) == maximum
    with pytest.raises(ValueError):
        scaled_to_decimal("-9223372036854775809", 0)
    with pytest.raises(ValueError):
        scaled_to_decimal("9223372036854775808", 0)
    with pytest.raises(ValueError):
        decimal_to_scaled(Decimal("-9223372036854775809"), 0)
    with pytest.raises(ValueError):
        decimal_to_scaled(Decimal("9223372036854775808"), 0)


def test_rejects_float_amount() -> None:
    with pytest.raises(TypeError):
        decimal_to_scaled(1.25, 2)  # type: ignore[arg-type]
