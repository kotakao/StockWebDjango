"""watchlist 純商業邏輯（spec §3.2）：組裝自選股行情/估值與持股損益。

不碰 HTTP、不寫 DB；透過 market selectors 唯讀讀取 market 庫。
容錯原則：個別代號缺行情以 None 帶出，不使整包失敗；watchlist/holdings 皆空回空清單。
損益計算：
- 市值＝shares*close
- 未實現損益＝(close-avg_cost)*shares
- 報酬率＝(close-avg_cost)/avg_cost*100（avg_cost 為 0/NULL 時回 None）
"""

from apps.market import selectors


def _pct_change(today: float | None, yesterday: float | None) -> float | None:
    """漲跌幅％＝(今收-昨收)/昨收*100；缺值或昨收為 0 回 None。"""
    if today is None or yesterday in (None, 0):
        return None
    return round((today - yesterday) / yesterday * 100, 2)


def _watchlist_row(code: str) -> dict:
    """單一自選股：最新收盤＋漲跌%（最新兩日）＋最新估值（pe/pb/殖利率）。缺料填 None。"""
    quotes = selectors.latest_daily_quotes(code, limit=2)
    close = quotes[0].get("close") if quotes else None
    prev = quotes[1].get("close") if len(quotes) > 1 else None
    val = selectors.latest_valuation(code)
    return {
        "code": code,
        "close": close,
        "change_pct": _pct_change(close, prev),
        "pe": val.get("pe") if val else None,
        "pb": val.get("pb") if val else None,
        "dividend_yield": val.get("dividend_yield") if val else None,
    }


def _holding_row(row: dict) -> dict:
    """單一持股：附最新收盤並計算市值、未實現損益、報酬率。缺收盤則相關值為 None。"""
    code = row["code"]
    shares = row.get("shares")
    avg_cost = row.get("avg_cost")
    quotes = selectors.latest_daily_quotes(code, limit=1)
    close = quotes[0].get("close") if quotes else None

    market_value = unrealized_pnl = return_pct = None
    if close is not None and shares is not None:
        market_value = round(close * shares, 2)
        if avg_cost is not None:
            unrealized_pnl = round((close - avg_cost) * shares, 2)
    if close is not None and avg_cost not in (None, 0):
        return_pct = round((close - avg_cost) / avg_cost * 100, 2)

    return {
        "code": code,
        "shares": shares,
        "avg_cost": avg_cost,
        "close": close,
        "market_value": market_value,
        "unrealized_pnl": unrealized_pnl,
        "return_pct": return_pct,
    }


def build_watchlist_summary(user_id: str) -> dict:
    """組裝某 user_id 的自選股與持股彙整（唯讀，回傳可 JSON 序列化的 dict）。

    watchlist 與 holdings 皆空時，各回空清單（呼叫端回 200）。
    """
    codes = selectors.watchlist_codes(user_id)
    holdings = selectors.holdings_rows(user_id)
    return {
        "user_id": user_id,
        "watchlist": [_watchlist_row(code) for code in codes],
        "holdings": [_holding_row(row) for row in holdings],
    }
