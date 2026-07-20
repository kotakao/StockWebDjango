"""market 庫唯讀查詢函數（spec §3.2）：進 DB、出 dict，不含商業邏輯。

鐵律：僅 SELECT，嚴禁任何寫入；查詢一律走 market 連線（Router 亦會導向）。
"""

from datetime import date, timedelta

from django.db.models import Max

from .models import (
    DailyQuote,
    DividendEvent,
    Holding,
    Institutional,
    InvestorConference,
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


# 月營收對比表（D9）回傳欄位（year_month ISO YYYY-MM 字典序即時序）。
_REVENUE_ROW_FIELDS = (
    "year_month",
    "revenue",
    "mom_pct",
    "yoy_pct",
    "cum_revenue",
    "cum_yoy_pct",
)


def monthly_revenue_rows(code: str) -> list[dict]:
    """取某代號「全部」月份的月營收列，依 year_month 新到舊；查無回空清單。

    每檔每年至多 12 筆、量小，不設筆數上限（spec §12 D9）。
    """
    return list(
        MonthlyRevenue.objects.using("market")
        .filter(code=code)
        .order_by("-year_month")
        .values(*_REVENUE_ROW_FIELDS)
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


# ---- 法說會（D6）所需唯讀查詢：investor_conferences（DC-K 入庫）----

# 兩清單共用回傳欄位（ISO 日期字串可直接比較排序）。
_CONFERENCE_FIELDS = ("market", "code", "name", "subject", "fact_date", "announce_date")


def upcoming_conferences(days: int, today: str | None = None) -> list[dict]:
    """即將召開：fact_date 介於今日與今日+days（含），依 fact_date 舊到新。

    ISO 日期字串字典序即時序，直接以字串比較。fact_date 為 NULL 者不符 __gte，
    自然排除（不入 upcoming）。today 預設今日，供測試注入邊界。
    """
    today = today or date.today().isoformat()
    end = (date.fromisoformat(today) + timedelta(days=days)).isoformat()
    return list(
        InvestorConference.objects.using("market")
        .filter(fact_date__gte=today, fact_date__lte=end)
        .order_by("fact_date")
        .values(*_CONFERENCE_FIELDS)
    )


def recent_conference_announcements(limit: int = 20) -> list[dict]:
    """近期公告：依 announce_date + announce_time 新到舊，取前 limit 筆。"""
    return list(
        InvestorConference.objects.using("market")
        .order_by("-announce_date", "-announce_time")
        .values(*_CONFERENCE_FIELDS)[:limit]
    )


# ---- 行事曆（D7）所需唯讀查詢：dividend_events 與 investor_conferences 的日期窗 ----

# 除權息回傳欄位（對照 dividend_events；ex_date ISO 字串可直接比較排序）。
_DIVIDEND_FIELDS = (
    "market",
    "code",
    "name",
    "event_type",
    "ex_date",
    "cash_dividend",
    "stock_ratio",
)


def dividend_events_between(start: str, end: str) -> list[dict]:
    """除權息事件：ex_date 介於 start 與 end（含），依 ex_date、market、code 排序。

    start/end 為 ISO YYYY-MM-DD 字串（字典序即時序）；區間外不入列，空區間回空清單。
    """
    return list(
        DividendEvent.objects.using("market")
        .filter(ex_date__gte=start, ex_date__lte=end)
        .order_by("ex_date", "market", "code")
        .values(*_DIVIDEND_FIELDS)
    )


def conference_dates_between(start: str, end: str) -> list[dict]:
    """法說會日期：fact_date 介於 start 與 end（含），依 fact_date、market、code 排序。

    fact_date 為 NULL 者不符 __gte，自然排除。回傳含月曆所需欄位。
    """
    return list(
        InvestorConference.objects.using("market")
        .filter(fact_date__gte=start, fact_date__lte=end)
        .order_by("fact_date", "market", "code")
        .values("market", "code", "name", "subject", "fact_date")
    )


# ---- 條件選股（D8）所需唯讀查詢：最新交易日全體行情 LEFT JOIN 同日估值 ----

# 條件選股基底所需行情欄位（對照 daily_quotes）。
_SCREENER_QUOTE_FIELDS = ("market", "code", "name", "close", "change", "volume")


def quotes_with_valuation(quote_date: str) -> list[dict]:
    """某交易日全體 daily_quotes 列，LEFT JOIN 同日 valuation（以 market+code 對齊）。

    valuation 缺列時 pe/pb/dividend_yield 為 None。以兩次查詢在 Python 端合併
    （個股約兩千檔、單日資料量小，dict 對齊即足）。回傳每列含行情欄位＋pe/pb/dividend_yield。
    """
    quotes = list(
        DailyQuote.objects.using("market")
        .filter(date=quote_date)
        .values(*_SCREENER_QUOTE_FIELDS)
    )
    vals = {
        (v["market"], v["code"]): v
        for v in Valuation.objects.using("market")
        .filter(date=quote_date)
        .values("market", "code", "pe", "pb", "dividend_yield")
    }
    for q in quotes:
        v = vals.get((q["market"], q["code"]))
        q["pe"] = v["pe"] if v else None
        q["pb"] = v["pb"] if v else None
        q["dividend_yield"] = v["dividend_yield"] if v else None
    return quotes


# ---- 個股 K 線（D10）所需唯讀查詢：日 K、三大法人、依代號查除權息事件 ----

# K 線所需行情欄位（對照 daily_quotes；還原價由 service 端計算，不動 DB）。
_QUOTE_KLINE_FIELDS = ("date", "open", "high", "low", "close", "volume")


def daily_quotes_series(code: str, days: int) -> list[dict]:
    """取某代號最新 days 個交易日行情（date 新到舊），供 K 線序列組裝與前復權。

    回傳每列含 OHLCV 欄位（缺值保留 None）；由 service 端反轉為舊到新並套用還原價。
    """
    return list(
        DailyQuote.objects.using("market")
        .filter(code=code)
        .order_by("-date")
        .values(*_QUOTE_KLINE_FIELDS)[:days]
    )


def institutional_series(code: str, days: int) -> list[dict]:
    """取某代號最新 days 個交易日三大法人買賣超（date 新到舊）；查無回空清單。

    回傳每列含 date 與 foreign_net／trust_net／dealer_net（股數，缺值 None），
    供 service 端以 date 對齊行情序列並加總換算張數。
    """
    return list(
        Institutional.objects.using("market")
        .filter(code=code)
        .order_by("-date")
        .values("date", "foreign_net", "trust_net", "dealer_net")[:days]
    )


def dividend_events_for_code(code: str, start: str) -> list[dict]:
    """取某代號 ex_date >= start 的除權息事件（ex_date 新到舊），供前復權還原歷史價。

    對齊 StockDCBot MarketStore.get_dividend_events：以代號定位、start 為序列最舊日，
    區間外事件不入列。回傳含 ex_date／cash_dividend／stock_ratio。
    """
    return list(
        DividendEvent.objects.using("market")
        .filter(code=code, ex_date__gte=start)
        .order_by("-ex_date")
        .values("ex_date", "cash_dividend", "stock_ratio")
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
