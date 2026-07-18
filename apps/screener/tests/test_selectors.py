"""quotes_with_valuation join 單元測試（D8）：同日行情 LEFT JOIN 估值，valuation 缺列容錯。

以 market_db_ready fixture 建暫時 SQLite market 庫，以可寫連線造假資料（Django market 連線唯讀）。
"""

import sqlite3

from apps.market import selectors

_Q = "INSERT INTO daily_quotes (market,date,code,name,close,change,volume) VALUES (?,?,?,?,?,?,?)"
_V = "INSERT INTO valuation (market,date,code,pe,dividend_yield,pb) VALUES (?,?,?,?,?,?)"


def _exec(db_file, sql, rows):
    conn = sqlite3.connect(db_file)
    conn.executemany(sql, rows)
    conn.commit()
    conn.close()


def test_join_aligns_by_market_code(market_db_ready):
    """同日行情與估值以 market+code 對齊；有估值者帶入 pe/pb/dividend_yield。"""
    _exec(market_db_ready, _Q, [("TWSE", "2026-07-17", "2330", "台積電", 1000.0, 10.0, 5_000_000)])
    _exec(market_db_ready, _V, [("TWSE", "2026-07-17", "2330", 18.5, 2.1, 5.6)])

    rows = selectors.quotes_with_valuation("2026-07-17")

    assert len(rows) == 1
    r = rows[0]
    assert r["code"] == "2330"
    assert r["close"] == 1000.0
    assert r["change"] == 10.0
    assert r["volume"] == 5_000_000
    assert r["pe"] == 18.5
    assert r["pb"] == 5.6
    assert r["dividend_yield"] == 2.1


def test_missing_valuation_row_yields_none(market_db_ready):
    """valuation 無對應列 → pe/pb/dividend_yield 為 None（不漏行情列）。"""
    _exec(market_db_ready, _Q, [("TWSE", "2026-07-17", "1111", "無估值", 50.0, 1.0, 100_000)])

    rows = selectors.quotes_with_valuation("2026-07-17")

    assert len(rows) == 1
    r = rows[0]
    assert r["code"] == "1111"
    assert r["pe"] is None
    assert r["pb"] is None
    assert r["dividend_yield"] is None


def test_only_given_date_returned(market_db_ready):
    """僅回傳指定交易日的列（其他日期不入）。"""
    _exec(market_db_ready, _Q, [
        ("TWSE", "2026-07-16", "2330", "台積電", 990.0, -10.0, 1_000_000),
        ("TWSE", "2026-07-17", "2330", "台積電", 1000.0, 10.0, 2_000_000),
    ])

    rows = selectors.quotes_with_valuation("2026-07-17")

    assert [(r["code"], r["close"]) for r in rows] == [("2330", 1000.0)]
