"""GET /api/dashboard/summary API 測試：參數驗證、序列輸出、Redis 快取行為。

以 conftest 的 market_db fixture 建暫時 SQLite market 庫，直接以可寫連線造假資料
（Django 的 market 連線為唯讀，僅供讀取）。
"""

import sqlite3

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.market import selectors

client = APIClient()

# market_daily 欄位順序（對照 conftest 測試 schema）。
_COLS = (
    "market",
    "date",
    "index_close",
    "turnover",
    "up_count",
    "down_count",
    "foreign_net",
    "trust_net",
    "dealer_net",
    "margin_balance",
)


def _insert(db_file, rows: list[tuple]) -> None:
    """以獨立可寫 sqlite3 連線寫入 market_daily 假資料（非 Django 唯讀連線）。"""
    placeholders = ",".join(["?"] * len(_COLS))
    conn = sqlite3.connect(db_file)
    conn.executemany(
        f"INSERT INTO market_daily ({','.join(_COLS)}) VALUES ({placeholders})", rows
    )
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def _clear_cache():
    """每測試前後清快取，避免快取／節流狀態跨測試污染。"""
    cache.clear()
    yield
    cache.clear()


def _sample_rows():
    return [
        ("TWSE", "2026-07-08", 45000.0, 150_000_000.0, 10.0, 4.0, 1000.0, 2000.0, -1000.0, 600.0),
        ("TWSE", "2026-07-09", 45100.0, 300_000_000.0, 5.0, 8.0, 2000.0, None, 500.0, None),
    ]


def test_default_days_returns_200_and_series(market_db):
    """預設 days=60：200，含四序列，日期舊→新。"""
    _insert(market_db, _sample_rows())
    resp = client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["days"] == 60
    assert data["count"] == 2
    assert data["dates"] == ["2026-07-08", "2026-07-09"]
    # 外資 1000→1、2000→2 股→張 累積
    assert data["institution"]["foreign"] == [1.0, 3.0]
    assert data["index"]["turnover_100m"] == [1.5, 3.0]


def test_days_param_limits_rows(market_db):
    """days=1：只取最近 1 個交易日。"""
    _insert(market_db, _sample_rows())
    resp = client.get("/api/dashboard/summary?days=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["dates"] == ["2026-07-09"]


def test_invalid_days_non_integer_400(market_db):
    """days 非整數 → 400 {"error": ...}。"""
    resp = client.get("/api/dashboard/summary?days=abc")
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.parametrize("bad", ["0", "253", "-5"])
def test_days_out_of_range_400(market_db, bad):
    """days 超出 1~252 → 400 {"error": ...}。"""
    resp = client.get(f"/api/dashboard/summary?days={bad}")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_cache_second_call_does_not_requery(market_db, monkeypatch):
    """第二次相同 days 呼叫命中快取，不再查 market 庫（selector 僅呼叫一次）。"""
    _insert(market_db, _sample_rows())
    calls = {"n": 0}
    real = selectors.recent_market_daily

    def _counting(days, market="TWSE"):
        calls["n"] += 1
        return real(days, market)

    monkeypatch.setattr("apps.market.selectors.recent_market_daily", _counting)

    first = client.get("/api/dashboard/summary?days=30")
    second = client.get("/api/dashboard/summary?days=30")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert calls["n"] == 1  # 第二次由快取回應


def test_cache_key_populated(market_db):
    """快取以 key dashboard:{days} 存整包（前綴 swd:v1 由 CACHES 設定加上）。"""
    _insert(market_db, _sample_rows())
    client.get("/api/dashboard/summary?days=45")
    cached = cache.get("dashboard:45")
    assert cached is not None
    assert cached["days"] == 45
