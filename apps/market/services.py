"""market 純邏輯（spec §3.2）：前復權（還原價）演算法。

移植自姊妹專案 StockDCBot `analysis.adjust_history`——公式與測試數字以 Bot 端
`tests/test_analysis.py` 為權威（除息減現金股利、除權除以 (1+配股率)、除權息先減再除；
OHLC 四價同步調整、量不調整；由最新事件往回逐事件套用）。不碰 HTTP、不寫 DB。
"""

from collections.abc import Iterable

# 前復權調整的四個價格欄位（成交量不調整）。
_PRICE_KEYS = ("open", "high", "low", "close")


def adjust_history(history: list[dict], events: Iterable[dict]) -> list[dict]:
    """前復權：對行情列（日期新到舊，含 open/high/low/close）依除權息事件還原歷史價。

    由最新事件往回逐事件調整：對 ex_date 之前（date < ex_date）的每列，
    price = (price - 現金股利) / (1 + 配股率)；事件當日與其後不動。多事件由新到舊
    逐一疊加。回傳為輸入的複本（不動到輸入列）；成交量與其餘欄位原樣保留。

    對齊 StockDCBot analysis.adjust_history：呼叫端須自行過濾未來事件
    （ex_date <= 序列最新日），本函數僅依 date 比較套用。
    """
    adjusted = [dict(row) for row in history]
    for event in sorted(events, key=lambda e: e["ex_date"], reverse=True):
        ex_date = event["ex_date"]
        cash = event.get("cash_dividend") or 0.0
        divisor = 1.0 + (event.get("stock_ratio") or 0.0)
        for row in adjusted:
            row_date = row.get("date")
            if not row_date or row_date >= ex_date:
                continue
            for key in _PRICE_KEYS:
                value = row.get(key)
                if value is not None:
                    row[key] = (value - cash) / divisor
    return adjusted
