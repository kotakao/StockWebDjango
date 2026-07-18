"""市場 selectors 行事曆日期窗單元測試（D7）。

- dividend_events_between：ex_date 落於 [start, end]（含月初/月底邊界）；跨月不入列；
  依 ex_date、market、code 排序。
- conference_dates_between：fact_date 同上區間；NULL 不入列；依 fact_date、market、code。

以 market_db_ready fixture 建暫時 SQLite market 庫，以可寫連線造假資料（Django market 連線唯讀）。
"""

import sqlite3

from apps.market import selectors

_DIV_COLS = ("market", "code", "ex_date", "name", "event_type", "cash_dividend", "stock_ratio")
_CONF_COLS = ("market", "code", "announce_date", "announce_time", "name", "subject", "fact_date")


def _insert(db_file, table, cols, rows):
    """以獨立可寫 sqlite3 連線寫入假資料（非 Django 唯讀連線）。"""
    placeholders = ",".join(["?"] * len(cols))
    conn = sqlite3.connect(db_file)
    conn.executemany(
        f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
        rows,
    )
    conn.commit()
    conn.close()


def test_dividends_include_month_boundaries_exclude_cross_month(market_db_ready):
    """月初與月底邊界日入列；前一月最後一日與次月第一日不入列。"""
    _insert(market_db_ready, "dividend_events", _DIV_COLS, [
        ("TWSE", "1001", "2026-06-30", "甲", "現金", 1.0, None),   # 上月底 → 不入
        ("TWSE", "1002", "2026-07-01", "乙", "現金", 2.0, None),   # 月初邊界 → 入
        ("TWSE", "1003", "2026-07-31", "丙", "股票", None, 0.1),   # 月底邊界 → 入
        ("TWSE", "1004", "2026-08-01", "丁", "現金", 3.0, None),   # 次月初 → 不入
    ])

    rows = selectors.dividend_events_between("2026-07-01", "2026-07-31")

    assert [r["code"] for r in rows] == ["1002", "1003"]


def test_dividends_sorted_by_ex_date_market_code(market_db_ready):
    """同區間依 ex_date、market、code 排序。"""
    _insert(market_db_ready, "dividend_events", _DIV_COLS, [
        ("TWSE", "2002", "2026-07-10", "b", "現金", 1.0, None),
        ("TPEX", "2001", "2026-07-10", "a", "現金", 1.0, None),
        ("TWSE", "2003", "2026-07-05", "c", "現金", 1.0, None),
    ])

    rows = selectors.dividend_events_between("2026-07-01", "2026-07-31")

    # 07-05 先；同日 TPEX < TWSE；欄位齊備
    assert [(r["ex_date"], r["market"], r["code"]) for r in rows] == [
        ("2026-07-05", "TWSE", "2003"),
        ("2026-07-10", "TPEX", "2001"),
        ("2026-07-10", "TWSE", "2002"),
    ]
    assert set(rows[0]) == set(_DIV_COLS)


def test_dividends_empty_returns_empty_list(market_db_ready):
    """無資料 → 空清單。"""
    assert selectors.dividend_events_between("2026-07-01", "2026-07-31") == []


def test_conference_dates_window_and_null(market_db_ready):
    """fact_date 落於區間（含邊界）入列；跨月與 NULL 不入列；依 fact_date、market、code。"""
    # fact_date：上月底 3001 不入、月初 3002 入、月底 3003 入、NULL 3004 不入、次月 3005 不入
    _insert(market_db_ready, "investor_conferences", _CONF_COLS, [
        ("TWSE", "3001", "2026-06-01", "09:00:00", "甲", "法人說明會", "2026-06-30"),
        ("TWSE", "3002", "2026-06-01", "09:00:00", "乙", "法人說明會", "2026-07-01"),
        ("TWSE", "3003", "2026-06-01", "09:00:00", "丙", "法人說明會", "2026-07-31"),
        ("TWSE", "3004", "2026-06-01", "09:00:00", "丁", "法人說明會", None),
        ("TWSE", "3005", "2026-06-01", "09:00:00", "戊", "法人說明會", "2026-08-01"),
    ])

    rows = selectors.conference_dates_between("2026-07-01", "2026-07-31")

    assert [r["code"] for r in rows] == ["3002", "3003"]
    assert set(rows[0]) == {"market", "code", "name", "subject", "fact_date"}
