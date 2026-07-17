"""market 庫唯讀查詢函數（spec §3.2）：進 DB、出 dict，不含商業邏輯。

鐵律：僅 SELECT，嚴禁任何寫入；查詢一律走 market 連線（Router 亦會導向）。
"""

from django.db.models import Max

from .models import (
    DailyQuote,
    Holding,
    MarketDaily,
    MonthlyRevenue,
    QuarterlyFinancial,
    Valuation,
    Watchlist,
)

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


# ---- 個股快照（D3）所需唯讀查詢：以 code 定位，跨市場（code 於各市場唯一）----


def latest_trade_date() -> str | None:
    """daily_quotes 全庫最新交易日（spec §7 判定快照是否為最新之基準）。查無資料回 None。"""
    return DailyQuote.objects.using("market").aggregate(m=Max("date"))["m"]


def code_exists(code: str) -> bool:
    """daily_quotes 是否有此代號任一列（供 API 判定「查無代號」→ 400）。"""
    return DailyQuote.objects.using("market").filter(code=code).exists()


def latest_daily_quotes(code: str, limit: int = 2) -> list[dict]:
    """取某代號最新 limit 日行情（date 新到舊），供收盤價與漲跌幅計算。"""
    return list(
        DailyQuote.objects.using("market")
        .filter(code=code)
        .order_by("-date")
        .values("market", "date", "name", "close")[:limit]
    )


def latest_valuation(code: str) -> dict | None:
    """取某代號最新一日 valuation（pe/pb/dividend_yield）；查無回 None。"""
    return (
        Valuation.objects.using("market")
        .filter(code=code)
        .order_by("-date")
        .values("date", "pe", "pb", "dividend_yield")
        .first()
    )


def latest_monthly_revenue(code: str) -> dict | None:
    """取某代號最新月營收（year_month/yoy_pct/cum_yoy_pct）；查無回 None。"""
    return (
        MonthlyRevenue.objects.using("market")
        .filter(code=code)
        .order_by("-year_month")
        .values("year_month", "yoy_pct", "cum_yoy_pct")
        .first()
    )


# ---- 自選股與持股（D5）所需唯讀查詢：以 user_id 定位 ----


def watchlist_codes(user_id: str) -> list[str]:
    """某 user_id 的自選股代號清單（依 code 排序）；查無回空清單。"""
    return list(
        Watchlist.objects.using("market")
        .filter(user_id=user_id)
        .order_by("code")
        .values_list("code", flat=True)
    )


def holdings_rows(user_id: str) -> list[dict]:
    """某 user_id 的持股（code/shares/avg_cost，依 code 排序）；查無回空清單。"""
    return list(
        Holding.objects.using("market")
        .filter(user_id=user_id)
        .order_by("code")
        .values("code", "shares", "avg_cost")
    )


def latest_quarterly_financial(code: str) -> dict | None:
    """取某代號最新季損益（含營收與毛利/營益/EPS 原始值，比率由 service 計算）；查無回 None。"""
    return (
        QuarterlyFinancial.objects.using("market")
        .filter(code=code)
        .order_by("-year_quarter")
        .values("year_quarter", "revenue", "gross_profit", "operating_income", "eps")
        .first()
    )
