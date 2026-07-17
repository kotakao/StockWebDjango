"""stocks 純商業邏輯（spec §3.2）：自 market 庫既有表彙整個股單日快照。

不碰 HTTP、不寫 DB；輸入為代號，輸出為快照欄位 dict（供 task upsert）或 None（查無代號）。
比率一律讀取端計算：漲跌幅、毛利率、營業利益率；分母為 0/NULL 時回 None（容錯）。
"""

from apps.market import selectors


def _pct_change(today: float | None, yesterday: float | None) -> float | None:
    """漲跌幅％＝(今收-昨收)/昨收*100；缺值或昨收為 0 回 None。"""
    if today is None or yesterday in (None, 0):
        return None
    return round((today - yesterday) / yesterday * 100, 2)


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    """比率％＝分子/分母*100；分子缺或分母為 0/NULL 回 None。"""
    if numerator is None or denominator in (None, 0):
        return None
    return round(numerator / denominator * 100, 2)


def build_snapshot(code: str) -> dict | None:
    """彙整某代號最新快照。

    來源（各自缺漏容錯 NULL，不阻斷整體）：
    - daily_quotes 最新兩日 → trade_date、name、market、close、change_pct
    - valuation 最新日 → pe、pb、dividend_yield
    - monthly_revenue 最新月 → revenue_yoy、revenue_cum_yoy、revenue_month
    - quarterly_financials 最新季 → gross_margin、operating_margin、eps、quarter

    查無此代號（daily_quotes 無列）回 None，供 API 轉 400。
    """
    quotes = selectors.latest_daily_quotes(code, limit=2)
    if not quotes:
        return None

    latest = quotes[0]
    prev = quotes[1] if len(quotes) > 1 else None
    close = latest.get("close")
    change_pct = _pct_change(close, prev.get("close") if prev else None)

    val = selectors.latest_valuation(code)
    rev = selectors.latest_monthly_revenue(code)
    fin = selectors.latest_quarterly_financial(code)

    gross_margin = operating_margin = eps = quarter = None
    if fin:
        revenue_q = fin.get("revenue")
        gross_margin = _ratio(fin.get("gross_profit"), revenue_q)
        operating_margin = _ratio(fin.get("operating_income"), revenue_q)
        eps = fin.get("eps")
        quarter = fin.get("year_quarter")

    return {
        "code": code,
        "name": latest.get("name"),
        "market": latest.get("market"),
        "trade_date": latest.get("date"),
        "close": close,
        "change_pct": change_pct,
        "pe": val.get("pe") if val else None,
        "pb": val.get("pb") if val else None,
        "dividend_yield": val.get("dividend_yield") if val else None,
        "revenue_yoy": rev.get("yoy_pct") if rev else None,
        "revenue_cum_yoy": rev.get("cum_yoy_pct") if rev else None,
        "revenue_month": rev.get("year_month") if rev else None,
        "gross_margin": gross_margin,
        "operating_margin": operating_margin,
        "eps": eps,
        "quarter": quarter,
    }
