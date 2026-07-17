"""市場 selectors 法說會查詢單元測試（D6）。

- upcoming_conferences：日期窗含邊界日（今日、今日+days）；fact_date NULL 不入 upcoming；依舊到新。
- recent_conference_announcements：依 announce_date+announce_time 新到舊、取 limit。

以 market_db fixture 建暫時 SQLite market 庫，直接以可寫連線造假資料（Django market 連線唯讀）。
"""

import sqlite3

from apps.market import selectors

_COLS = (
    "market",
    "code",
    "announce_date",
    "announce_time",
    "name",
    "subject",
    "matched_clause",
    "fact_date",
    "description",
    "report_date",
)


def _insert(db_file, rows: list[dict]) -> None:
    """以獨立可寫 sqlite3 連線寫入 investor_conferences 假資料（非 Django 唯讀連線）。"""
    placeholders = ",".join(["?"] * len(_COLS))
    tuples = [tuple(r.get(c) for c in _COLS) for r in rows]
    conn = sqlite3.connect(db_file)
    conn.executemany(
        f"INSERT INTO investor_conferences ({','.join(_COLS)}) VALUES ({placeholders})",
        tuples,
    )
    conn.commit()
    conn.close()


def _row(code, announce_date, announce_time, fact_date, **kw):
    base = {
        "market": "TWSE",
        "code": code,
        "announce_date": announce_date,
        "announce_time": announce_time,
        "name": kw.get("name", f"公司{code}"),
        "subject": kw.get("subject", "受邀參加法人說明會"),
        "matched_clause": None,
        "fact_date": fact_date,
        "description": None,
        "report_date": None,
    }
    return base


def test_upcoming_includes_boundary_days(market_db_ready):
    """fact_date 落在今日與今日+days（含）者入 upcoming；窗外不入。"""
    today = "2026-07-18"
    _insert(market_db_ready, [
        _row("1001", "2026-07-10", "09:00:00", "2026-07-17"),  # 昨日 → 窗外
        _row("1002", "2026-07-10", "09:00:00", "2026-07-18"),  # 今日邊界 → 入
        _row("1003", "2026-07-10", "09:00:00", "2026-07-25"),  # 今日+7 邊界 → 入
        _row("1004", "2026-07-10", "09:00:00", "2026-07-26"),  # 窗外 → 不入
    ])

    rows = selectors.upcoming_conferences(7, today=today)

    assert [r["code"] for r in rows] == ["1002", "1003"]


def test_upcoming_sorted_by_fact_date_ascending(market_db_ready):
    """upcoming 依 fact_date 舊到新。"""
    today = "2026-07-18"
    _insert(market_db_ready, [
        _row("2001", "2026-07-10", "09:00:00", "2026-07-24"),
        _row("2002", "2026-07-10", "09:00:00", "2026-07-20"),
        _row("2003", "2026-07-10", "09:00:00", "2026-07-22"),
    ])

    rows = selectors.upcoming_conferences(30, today=today)

    assert [r["fact_date"] for r in rows] == ["2026-07-20", "2026-07-22", "2026-07-24"]


def test_upcoming_excludes_null_fact_date(market_db_ready):
    """fact_date 為 NULL 者不入 upcoming（無召開日）。"""
    today = "2026-07-18"
    _insert(market_db_ready, [
        _row("3001", "2026-07-10", "09:00:00", None),
        _row("3002", "2026-07-10", "09:00:00", "2026-07-20"),
    ])

    rows = selectors.upcoming_conferences(30, today=today)

    assert [r["code"] for r in rows] == ["3002"]


def test_recent_sorted_by_announce_desc_and_limited(market_db_ready):
    """近期公告依 announce_date+announce_time 新到舊，並受 limit 限制。"""
    _insert(market_db_ready, [
        _row("4001", "2026-07-15", "09:00:00", "2026-08-01"),
        _row("4002", "2026-07-17", "14:30:00", "2026-08-02"),
        _row("4003", "2026-07-17", "09:00:00", "2026-08-03"),
        _row("4004", "2026-07-16", "10:00:00", "2026-08-04"),
    ])

    rows = selectors.recent_conference_announcements(limit=3)

    # 17 14:30 > 17 09:00 > 16 10:00 > 15（被 limit 截掉）
    assert [r["code"] for r in rows] == ["4002", "4003", "4004"]


def test_recent_empty_returns_empty_list(market_db_ready):
    """無資料 → 空清單。"""
    assert selectors.recent_conference_announcements() == []
    assert selectors.upcoming_conferences(30, today="2026-07-18") == []
