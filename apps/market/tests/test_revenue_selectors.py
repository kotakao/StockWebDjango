"""monthly_revenue_rows 單元測試（D9）：全月份新到舊排序、欄位齊全、NULL 容錯、查無空清單。

以 market_db_ready fixture 建暫時 SQLite market 庫，以可寫連線造假資料
（Django 的 market 連線唯讀）。
"""

import sqlite3

from apps.market import selectors

_R = (
    "INSERT INTO monthly_revenue "
    "(market,code,year_month,name,revenue,mom_pct,yoy_pct,cum_revenue,cum_yoy_pct) "
    "VALUES (?,?,?,?,?,?,?,?,?)"
)


def _exec(db_file, rows):
    conn = sqlite3.connect(db_file)
    conn.executemany(_R, rows)
    conn.commit()
    conn.close()


def test_returns_all_months_newest_first(market_db_ready):
    """回傳該代號全部月份，依 year_month 新到舊排序，欄位齊全。"""
    _exec(market_db_ready, [
        ("TWSE", "2330", "2026-04", "台積電", 1000.0, 1.0, 10.0, 4000.0, 12.0),
        ("TWSE", "2330", "2026-06", "台積電", 3000.0, 3.0, 30.0, 9000.0, 20.0),
        ("TWSE", "2330", "2026-05", "台積電", 2000.0, 2.0, 20.0, 6000.0, 15.0),
    ])

    rows = selectors.monthly_revenue_rows("2330")

    assert [r["year_month"] for r in rows] == ["2026-06", "2026-05", "2026-04"]
    assert set(rows[0]) == {
        "year_month", "revenue", "mom_pct", "yoy_pct", "cum_revenue", "cum_yoy_pct",
    }
    assert rows[0]["revenue"] == 3000.0
    assert rows[0]["cum_yoy_pct"] == 20.0


def test_null_fields_preserved(market_db_ready):
    """來源缺漏欄位保留為 None。"""
    _exec(market_db_ready, [
        ("TWSE", "1111", "2026-06", "缺漏", 500.0, None, None, None, None),
    ])

    rows = selectors.monthly_revenue_rows("1111")

    assert len(rows) == 1
    assert rows[0]["mom_pct"] is None
    assert rows[0]["yoy_pct"] is None
    assert rows[0]["cum_revenue"] is None


def test_unknown_code_returns_empty(market_db_ready):
    """查無代號 → 空清單（不報錯）。"""
    assert selectors.monthly_revenue_rows("9999") == []
