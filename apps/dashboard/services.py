"""dashboard 純商業邏輯（spec §3.2）：組裝儀表板四序列，不碰 HTTP、不查 DB。

輸入為 selectors 取出的 market_daily 列（dict，日期由舊到新）；
輸出為前端四張圖卡所需序列。缺欄容錯：
- 原始序列（指數、成交金額、漲跌家數、融資餘額）缺值以 None 帶出。
- 累積序列（三大法人買賣超、A/D Line）缺值視為當日 0，維持連續累積曲線。
"""

from collections.abc import Callable

SHARES_PER_LOT = 1000  # 股→張換算：1 張 = 1000 股
YI = 100_000_000  # 億：金額（元）→億元換算


def _round(value: float | None, ndigits: int) -> float | None:
    """None 保持 None，否則四捨五入至指定小數位。"""
    return None if value is None else round(value, ndigits)


def _raw_series(rows: list[dict], field: str, transform: Callable[[float], float] | None = None):
    """原始序列：逐列取欄位，缺值（None）保留 None，可選數值轉換。"""
    out: list[float | None] = []
    for row in rows:
        value = row.get(field)
        if value is None:
            out.append(None)
        else:
            out.append(transform(value) if transform else value)
    return out


def _cumulative(rows: list[dict], value_of: Callable[[dict], float | None]) -> list[float]:
    """累積序列：逐列取值（None 視為 0），輸出當日的累積總和。"""
    out: list[float] = []
    running = 0.0
    for row in rows:
        value = value_of(row)
        if value is not None:
            running += value
        out.append(running)
    return out


def _lots(shares: float | None) -> float | None:
    """股→張（÷1000）；None 保持 None。"""
    return None if shares is None else shares / SHARES_PER_LOT


def build_dashboard_summary(rows: list[dict], days: int) -> dict:
    """將 market_daily 列組裝為儀表板四序列（回傳可 JSON 序列化的 dict）。

    rows：日期由舊到新的 market_daily dict 列表。
    四序列：
      1. institution：三大法人（外資/投信/自營商）買賣超「張」的累積和序列。
      2. breadth：漲跌家數與 A/D Line（每日 up-down 的累積）。
      3. index：指數收盤與成交金額（億元）。
      4. margin：融資餘額趨勢。
    """
    dates = [row.get("date") for row in rows]

    institution = {
        "foreign": [
            _round(v, 3) for v in _cumulative(rows, lambda r: _lots(r.get("foreign_net")))
        ],
        "trust": [
            _round(v, 3) for v in _cumulative(rows, lambda r: _lots(r.get("trust_net")))
        ],
        "dealer": [
            _round(v, 3) for v in _cumulative(rows, lambda r: _lots(r.get("dealer_net")))
        ],
    }

    def _up_minus_down(row: dict) -> float | None:
        up, down = row.get("up_count"), row.get("down_count")
        if up is None and down is None:
            return None
        return (up or 0) - (down or 0)

    breadth = {
        "up": _raw_series(rows, "up_count"),
        "down": _raw_series(rows, "down_count"),
        "ad_line": _cumulative(rows, _up_minus_down),
    }

    index = {
        "close": _raw_series(rows, "index_close"),
        "turnover_100m": _raw_series(rows, "turnover", lambda v: round(v / YI, 2)),
    }

    margin = {"balance": _raw_series(rows, "margin_balance")}

    return {
        "days": days,
        "count": len(rows),
        "dates": dates,
        "institution": institution,
        "breadth": breadth,
        "index": index,
        "margin": margin,
    }
