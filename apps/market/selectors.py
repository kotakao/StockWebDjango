"""market 庫唯讀查詢函數（spec §3.2）：進 DB、出 dict，不含商業邏輯。

鐵律：僅 SELECT，嚴禁任何寫入；查詢一律走 market 連線（Router 亦會導向）。
"""

from .models import MarketDaily

# 儀表板序列所需欄位（對照 market_daily）。
_SUMMARY_FIELDS = (
    "date",
    "index_close",
    "turnover",
    "up_count",
    "down_count",
    "foreign_net",
    "trust_net",
    "dealer_net",
    "margin_balance",
)


def recent_market_daily(days: int, market: str = "TWSE") -> list[dict]:
    """取 market_daily 近 days 個交易日資料，日期由舊到新排序。

    先以日期新到舊取前 days 筆（確保拿到最近的），再反轉為舊到新供序列組裝。
    回傳每列為 dict（含 _SUMMARY_FIELDS 欄位），缺值保留 None。
    """
    rows = list(
        MarketDaily.objects.using("market")
        .filter(market=market)
        .order_by("-date")
        .values(*_SUMMARY_FIELDS)[:days]
    )
    rows.reverse()
    return rows
