"""共用 query 參數解析工具（DRF views 共用；錯誤格式見 spec §5）。"""

from rest_framework.exceptions import ValidationError


def parse_bounded_int(
    raw: str | None, *, default: int, lo: int, hi: int, label: str = "days"
) -> int:
    """解析有界整數 query 參數：raw 為 None／空字串回 default；
    非整數或超出 [lo, hi] 拋 DRF ValidationError（→400 {"error": ...}）。
    """
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"{label} 必須為整數") from None
    if not (lo <= value <= hi):
        raise ValidationError(f"{label} 需介於 {lo} 與 {hi}")
    return value
