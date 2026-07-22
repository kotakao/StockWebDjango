"""parse_bounded_int 共用參數解析測試：default／合法值／非整數／超界。"""

import pytest
from rest_framework.exceptions import ValidationError

from apps.core.params import parse_bounded_int


@pytest.mark.parametrize("raw", [None, ""])
def test_missing_returns_default(raw):
    """raw 為 None 或空字串 → 回 default。"""
    assert parse_bounded_int(raw, default=60, lo=1, hi=252) == 60


@pytest.mark.parametrize(("raw", "expected"), [("1", 1), ("5", 5), ("252", 252)])
def test_valid_returns_int(raw, expected):
    """合法整數字串（含上下界）→ 回 int。"""
    assert parse_bounded_int(raw, default=60, lo=1, hi=252) == expected


@pytest.mark.parametrize("raw", ["abc", "1.5"])
def test_non_integer_raises(raw):
    """非整數 → ValidationError，訊息含「必須為整數」。"""
    with pytest.raises(ValidationError, match="days 必須為整數"):
        parse_bounded_int(raw, default=60, lo=1, hi=252)


@pytest.mark.parametrize("raw", ["0", "253", "-5"])
def test_out_of_bounds_raises(raw):
    """超出 [lo, hi] → ValidationError，訊息含上下界。"""
    with pytest.raises(ValidationError, match="days 需介於 1 與 252"):
        parse_bounded_int(raw, default=60, lo=1, hi=252)
