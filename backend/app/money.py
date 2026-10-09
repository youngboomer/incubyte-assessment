import re
from decimal import ROUND_HALF_EVEN, Decimal

# CAST(salary_usd_scaled AS INTEGER) is a signed 64-bit SQLite integer.
_INT64_MIN = -9_223_372_036_854_775_808
_INT64_MAX = 9_223_372_036_854_775_807
_SCALED_RE = re.compile(r"^-?\d+$")


def scaled_to_decimal(scaled: str, scale: int) -> Decimal:
    _require_scale(scale)
    _parse_scaled_int(scaled)
    return Decimal(scaled) / (Decimal(10) ** scale)


def decimal_to_scaled(amount: Decimal, scale: int) -> str:
    if not isinstance(amount, Decimal):
        raise TypeError("amount must be Decimal")
    if not amount.is_finite():
        raise ValueError("amount must be finite")
    _require_scale(scale)
    factor = Decimal(10) ** scale
    digits = (amount * factor).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
    value = int(digits)
    if Decimal(value) != digits:
        raise ValueError("scaled amount is not an integer")
    if value < _INT64_MIN or value > _INT64_MAX:
        raise ValueError("scaled amount must fit in signed int64")
    return str(value)


def _require_scale(scale: int) -> None:
    if isinstance(scale, bool) or not isinstance(scale, int):
        raise TypeError("scale must be an int")
    if scale < 0:
        raise ValueError("scale must be >= 0")


def _parse_scaled_int(scaled: str) -> int:
    if not isinstance(scaled, str) or _SCALED_RE.fullmatch(scaled) is None:
        raise ValueError("scaled amount must match ^-?\\d+$")
    value = int(scaled)
    if value < _INT64_MIN or value > _INT64_MAX:
        raise ValueError("scaled amount must fit in signed int64")
    return value
