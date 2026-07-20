"""build_quotes 序列組裝單元測試（D10）：舊到新、法人÷1000張、缺日容錯、前復權整合。

以 conftest 的 market_db fixture 建暫時 SQLite market 庫，以可寫連線造假資料
（Django 的 market 連線唯讀，僅供讀取）。
"""

import sqlite3

from apps.stocks import services

_Q = (
    "INSERT INTO daily_quotes (market,date,code,name,open,high,low,close,change,volume) "
    "VALUES (?,?,?,?,?,?,?,?,?,?)"
)
_I = (
    "INSERT INTO institutional (market,date,code,name,foreign_net,trust_net,dealer_net) "
    "VALUES (?,?,?,?,?,?,?)"
)
_D = (
    "INSERT INTO dividend_events (market,code,ex_date,name,event_type,cash_dividend,stock_ratio) "
    "VALUES (?,?,?,?,?,?,?)"
)


def _seed(db_file, quotes=(), inst=(), events=()):
    conn = sqlite3.connect(db_file)
    if quotes:
        conn.executemany(_Q, quotes)
    if inst:
        conn.executemany(_I, inst)
    if events:
        conn.executemany(_D, events)
    conn.commit()
    conn.close()


def test_unknown_code_returns_empty(market_db):
    """查無代號 → 空清單。"""
    assert services.build_quotes("9999", 252, True) == []


def test_series_oldest_to_newest_with_inst_lots(market_db):
    """序列日期舊到新；三大法人淨額為 (外資+投信+自營)÷1000 張。"""
    _seed(
        market_db,
        quotes=[
            ("TWSE", "2026-06-01", "2330", "台積電", 100.0, 101.0, 99.0, 100.0, 0.0, 5000.0),
            ("TWSE", "2026-06-02", "2330", "台積電", 100.0, 102.0, 100.0, 101.0, 1.0, 6000.0),
        ],
        inst=[
            ("TWSE", "2026-06-01", "2330", "台積電", 1_000_000.0, 500_000.0, -200_000.0),
            ("TWSE", "2026-06-02", "2330", "台積電", 2_000_000.0, 0.0, 0.0),
        ],
    )

    out = services.build_quotes("2330", 252, adjusted=False)

    assert [r["date"] for r in out] == ["2026-06-01", "2026-06-02"]
    assert out[0]["inst_net"] == 1300  # (1_000_000+500_000-200_000)/1000
    assert out[1]["inst_net"] == 2000
    assert out[0]["close"] == 100.0
    assert out[0]["volume"] == 5000.0


def test_missing_institutional_day_tolerated(market_db):
    """法人缺日 → inst_net 為 None（不影響行情列）；列內個別欄缺值以 0 計。"""
    _seed(
        market_db,
        quotes=[
            ("TWSE", "2026-06-01", "2330", "台積電", 100.0, 101.0, 99.0, 100.0, 0.0, 5000.0),
            ("TWSE", "2026-06-02", "2330", "台積電", 100.0, 102.0, 100.0, 101.0, 1.0, 6000.0),
        ],
        inst=[
            # 只有 06-02 有法人資料，且投信/自營缺值（None）
            ("TWSE", "2026-06-02", "2330", "台積電", 3_000_000.0, None, None),
        ],
    )

    out = services.build_quotes("2330", 252, adjusted=False)

    assert out[0]["inst_net"] is None  # 06-01 無法人列
    assert out[1]["inst_net"] == 3000  # 缺值以 0 計


def test_adjusted_applies_only_in_range_non_future(market_db):
    """前復權：僅套用序列日期範圍內且非未來的事件；除息當日與其後不動。"""
    _seed(
        market_db,
        quotes=[
            ("TWSE", "2026-06-01", "2330", "台積電", 120.0, 120.0, 118.0, 120.0, 0.0, 1000.0),
            ("TWSE", "2026-06-02", "2330", "台積電", 101.0, 101.0, 100.0, 101.0, 0.0, 1000.0),
        ],
        events=[
            ("TWSE", "2330", "2026-06-02", "台積電", "除息", 20.0, 0.0),  # 範圍內
            ("TWSE", "2330", "2026-07-01", "台積電", "除息", 20.0, 0.0),  # 未來日，不套用
        ],
    )

    out = services.build_quotes("2330", 252, adjusted=True)

    assert out[1]["close"] == 101.0  # 除息當日不動
    assert out[0]["close"] == 100.0  # 06-01: 120-20，未來事件不提前調整

    # 未還原時保留原始跳空
    raw = services.build_quotes("2330", 252, adjusted=False)
    assert raw[0]["close"] == 120.0
