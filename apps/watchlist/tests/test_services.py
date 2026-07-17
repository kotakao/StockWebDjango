"""build_watchlist_summary 單元測試：自選股行情/估值、持股損益（含 avg_cost 0/NULL、缺行情）。

以 market_db fixture 建暫時 SQLite market 庫，直接以可寫連線造假資料（Django market 連線唯讀）。
"""

import sqlite3

from apps.watchlist.services import build_watchlist_summary


def _exec(db_file, sql: str, rows: list[tuple]) -> None:
    """以獨立可寫 sqlite3 連線寫入假資料（非 Django 唯讀連線）。"""
    conn = sqlite3.connect(db_file)
    conn.executemany(sql, rows)
    conn.commit()
    conn.close()


_Q = "INSERT INTO daily_quotes (market,date,code,name,close) VALUES (?,?,?,?,?)"
_V = "INSERT INTO valuation (market,date,code,pe,dividend_yield,pb) VALUES (?,?,?,?,?,?)"
_W = "INSERT INTO watchlist (user_id,code) VALUES (?,?)"
_H = "INSERT INTO holdings (user_id,code,shares,avg_cost,updated_at) VALUES (?,?,?,?,?)"


def test_empty_returns_empty_lists(market_db):
    """watchlist 與 holdings 皆空 → 兩區塊回空清單。"""
    summary = build_watchlist_summary("0")
    assert summary == {"user_id": "0", "watchlist": [], "holdings": []}


def test_watchlist_row_with_quote_and_valuation(market_db):
    """自選股附最新收盤、漲跌%（最新兩日）與最新估值。"""
    _exec(market_db, _Q, [
        ("TWSE", "2026-07-10", "2330", "台積電", 1000.0),
        ("TWSE", "2026-07-13", "2330", "台積電", 1050.0),
    ])
    _exec(market_db, _V, [("TWSE", "2026-07-13", "2330", 18.5, 2.1, 5.6)])
    _exec(market_db, _W, [("0", "2330")])

    summary = build_watchlist_summary("0")

    assert len(summary["watchlist"]) == 1
    row = summary["watchlist"][0]
    assert row["code"] == "2330"
    assert row["close"] == 1050.0
    assert row["change_pct"] == 5.0  # (1050-1000)/1000*100
    assert row["pe"] == 18.5
    assert row["pb"] == 5.6
    assert row["dividend_yield"] == 2.1


def test_watchlist_missing_quote_tolerates_null(market_db):
    """自選股缺行情：整包不失敗，該檔行情/估值欄位為 None。"""
    _exec(market_db, _W, [("0", "9999")])

    summary = build_watchlist_summary("0")

    row = summary["watchlist"][0]
    assert row["code"] == "9999"
    assert row["close"] is None
    assert row["change_pct"] is None
    assert row["pe"] is None


def test_holding_pnl_calculation(market_db):
    """持股：市值＝shares*close、未實現＝(close-avg_cost)*shares、報酬率正確。"""
    _exec(market_db, _Q, [("TWSE", "2026-07-13", "2330", "台積電", 1050.0)])
    _exec(market_db, _H, [("0", "2330", 2.0, 1000.0, "2026-07-13")])

    row = build_watchlist_summary("0")["holdings"][0]

    assert row["close"] == 1050.0
    assert row["market_value"] == 2100.0  # 1050*2
    assert row["unrealized_pnl"] == 100.0  # (1050-1000)*2
    assert row["return_pct"] == 5.0  # (1050-1000)/1000*100


def test_holding_zero_or_null_avg_cost_return_pct_null(market_db):
    """avg_cost 為 0 或 NULL → 報酬率 None；未實現損益缺 avg_cost 時亦 None，但市值仍算。"""
    _exec(market_db, _Q, [
        ("TWSE", "2026-07-13", "1111", "零成本", 50.0),
        ("TWSE", "2026-07-13", "2222", "無成本", 80.0),
    ])
    _exec(market_db, _H, [
        ("0", "1111", 3.0, 0.0, "2026-07-13"),
        ("0", "2222", 4.0, None, "2026-07-13"),
    ])

    rows = {r["code"]: r for r in build_watchlist_summary("0")["holdings"]}

    zero = rows["1111"]
    assert zero["market_value"] == 150.0  # 50*3 仍計算
    assert zero["return_pct"] is None  # avg_cost 0 → None
    assert zero["unrealized_pnl"] == 150.0  # (50-0)*3

    null = rows["2222"]
    assert null["market_value"] == 320.0  # 80*4
    assert null["return_pct"] is None  # avg_cost NULL → None
    assert null["unrealized_pnl"] is None  # 缺 avg_cost 不算損益


def test_holding_missing_quote_tolerates_null(market_db):
    """持股缺行情：收盤/市值/損益/報酬率皆 None，不阻斷整包。"""
    _exec(market_db, _H, [("0", "9999", 5.0, 100.0, "2026-07-13")])

    row = build_watchlist_summary("0")["holdings"][0]

    assert row["close"] is None
    assert row["market_value"] is None
    assert row["unrealized_pnl"] is None
    assert row["return_pct"] is None
