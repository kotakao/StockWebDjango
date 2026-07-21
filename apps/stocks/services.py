"""stocks 純商業邏輯（spec §3.2）：自 market 庫既有表彙整個股單日快照。

不碰 HTTP、不寫 DB；輸入為代號，輸出為快照欄位 dict（供 task upsert）或 None（查無代號）。
比率一律讀取端計算：漲跌幅、毛利率、營業利益率；分母為 0/NULL 時回 None（容錯）。
"""

from apps.market import selectors
from apps.market import services as market_services


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


def _inst_net_lots(row: dict | None) -> int | None:
    """三大法人合計淨額（張）＝(外資+投信+自營)股數÷1000 四捨五入。

    缺日容錯：查無該日 institutional 列（row 為 None）回 None；列存在但個別法人
    欄位缺值以 0 計（部分缺漏不整列作廢）。
    """
    if row is None:
        return None
    total = (
        (row.get("foreign_net") or 0.0)
        + (row.get("trust_net") or 0.0)
        + (row.get("dealer_net") or 0.0)
    )
    return round(total / 1000)


def build_quotes(code: str, days: int, adjusted: bool) -> list[dict]:
    """組裝個股日 K 序列（日期舊到新）：OHLCV ＋ 三大法人淨額（張）。

    - 行情取 daily_quotes 最新 days 日（新到舊），前復權時套用還原價
      （事件僅取 ex_date 落在序列日期範圍內且非未來日者，對齊 Bot adjusted_history）。
    - 三大法人以 date 對齊（缺日 inst_net 回 None）。
    查無代號（daily_quotes 無列）回空清單。
    """
    history = selectors.daily_quotes_series(code, days)
    if not history:
        return []

    if adjusted:
        newest = history[0]["date"]
        oldest = history[-1]["date"]
        events = [
            e
            for e in selectors.dividend_events_for_code(code, oldest)
            if e["ex_date"] <= newest
        ]
        if events:
            history = market_services.adjust_history(history, events)

    inst_by_date = {r["date"]: r for r in selectors.institutional_series(code, days)}

    series = []
    for row in reversed(history):  # 反轉為舊到新
        series.append(
            {
                "date": row["date"],
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "volume": row.get("volume"),
                "inst_net": _inst_net_lots(inst_by_date.get(row["date"])),
            }
        )
    return series


def build_peers(code: str) -> dict:
    """組裝同業對比：同產業（company_profile.industry_code）全部個股的最新估值/營收/毛利率。

    來源（各自缺漏容錯 NULL，不阻斷整列）：
    - company_profile → 該股產業別（industry_code）與同業清單（code/name）
    - valuation 最新日 → pe/pb/dividend_yield
    - monthly_revenue 最新月 → revenue_yoy
    - quarterly_financials 最新季 → gross_margin（gross_profit/revenue 於讀取端計算）

    容錯：company_profile 表不存在或該股無產業資料時回 {"peers": [], "reason": <原因>}；
    正常回 {"peers": [...], "reason": None}，本股列標 is_self=True。
    """
    if not selectors.company_profile_available():
        return {"peers": [], "reason": "company_profile 表尚未建立（待部署機累積產業資料）"}

    anchor = selectors.company_profile_industry(code)
    if not anchor or not anchor.get("industry_code"):
        return {"peers": [], "reason": "查無此股的產業分類資料"}

    peers = []
    for profile in selectors.industry_peers(anchor["market"], anchor["industry_code"]):
        pcode = profile["code"]
        val = selectors.latest_valuation(pcode)
        rev = selectors.latest_monthly_revenue(pcode)
        fin = selectors.latest_quarterly_financial(pcode)
        gross_margin = _ratio(fin.get("gross_profit"), fin.get("revenue")) if fin else None
        peers.append(
            {
                "code": pcode,
                "name": profile.get("name"),
                "pe": val.get("pe") if val else None,
                "pb": val.get("pb") if val else None,
                "dividend_yield": val.get("dividend_yield") if val else None,
                "revenue_yoy": rev.get("yoy_pct") if rev else None,
                "gross_margin": gross_margin,
                "is_self": pcode == code,
            }
        )
    return {"peers": peers, "reason": None}
