"""build_snapshot 單元測試：來源齊全／缺漏／代號不存在／營收為 0（暫時 SQLite market fixture）。

以 market_db fixture 建暫時 SQLite market 庫，直接以可寫連線造假資料（Django market 連線唯讀）。
"""

import sqlite3

from apps.stocks.services import build_snapshot


def _exec(db_file, sql: str, rows: list[tuple]) -> None:
    """以獨立可寫 sqlite3 連線寫入假資料（非 Django 唯讀連線）。"""
    conn = sqlite3.connect(db_file)
    conn.executemany(sql, rows)
    conn.commit()
    conn.close()


_Q = "INSERT INTO daily_quotes (market,date,code,name,close) VALUES (?,?,?,?,?)"
_V = "INSERT INTO valuation (market,date,code,pe,dividend_yield,pb) VALUES (?,?,?,?,?,?)"
_R = (
    "INSERT INTO monthly_revenue (market,code,year_month,revenue,yoy_pct,cum_yoy_pct) "
    "VALUES (?,?,?,?,?,?)"
)
_F = (
    "INSERT INTO quarterly_financials "
    "(market,code,year_quarter,revenue,gross_profit,operating_income,eps) "
    "VALUES (?,?,?,?,?,?,?)"
)


def test_all_sources_complete(market_db):
    """四來源齊全：漲跌幅與毛利/營益率正確計算，指標齊備。"""
    _exec(market_db, _Q, [
        ("TWSE", "2026-07-10", "2330", "台積電", 1000.0),
        ("TWSE", "2026-07-13", "2330", "台積電", 1050.0),
    ])
    _exec(market_db, _V, [("TWSE", "2026-07-13", "2330", 18.5, 2.1, 5.6)])
    _exec(market_db, _R, [("TWSE", "2330", "2026-07", 2000.0, 30.0, 25.0)])
    _exec(market_db, _F, [("TWSE", "2330", "2026Q1", 500.0, 300.0, 200.0, 8.5)])

    snap = build_snapshot("2330")

    assert snap is not None
    assert snap["code"] == "2330"
    assert snap["name"] == "台積電"
    assert snap["market"] == "TWSE"
    assert snap["trade_date"] == "2026-07-13"
    assert snap["close"] == 1050.0
    assert snap["change_pct"] == 5.0  # (1050-1000)/1000*100
    assert snap["pe"] == 18.5
    assert snap["pb"] == 5.6
    assert snap["dividend_yield"] == 2.1
    assert snap["revenue_yoy"] == 30.0
    assert snap["revenue_cum_yoy"] == 25.0
    assert snap["revenue_month"] == "2026-07"
    assert snap["gross_margin"] == 60.0  # 300/500*100
    assert snap["operating_margin"] == 40.0  # 200/500*100
    assert snap["eps"] == 8.5
    assert snap["quarter"] == "2026Q1"


def test_partial_sources_tolerate_null(market_db):
    """僅 daily_quotes 單日、其餘來源缺漏：不阻斷，缺項為 None、change_pct 為 None。"""
    _exec(market_db, _Q, [("TWSE", "2026-07-13", "6666", "某公司", 42.0)])

    snap = build_snapshot("6666")

    assert snap is not None
    assert snap["close"] == 42.0
    assert snap["change_pct"] is None  # 僅一日無昨收
    assert snap["pe"] is None
    assert snap["revenue_yoy"] is None
    assert snap["gross_margin"] is None
    assert snap["eps"] is None
    assert snap["quarter"] is None


def test_code_not_found(market_db):
    """daily_quotes 無此代號 → 回 None（供 API 轉 400）。"""
    assert build_snapshot("9999") is None


def test_zero_revenue_yields_null_ratios(market_db):
    """季營收為 0 → 毛利率/營益率為 None（避免除以零）；eps 仍帶出。"""
    _exec(market_db, _Q, [("TWSE", "2026-07-13", "1111", "零營收", 10.0)])
    _exec(market_db, _F, [("TWSE", "1111", "2026Q1", 0.0, 5.0, 3.0, 0.1)])

    snap = build_snapshot("1111")

    assert snap["gross_margin"] is None
    assert snap["operating_margin"] is None
    assert snap["eps"] == 0.1
    assert snap["quarter"] == "2026Q1"
