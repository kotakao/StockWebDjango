"""GET /api/conferences/summary API 測試：參數驗證、空清單、序列輸出、Redis 快取行為。

以 conftest 的 market_db fixture 建暫時 SQLite market 庫，直接以可寫連線造假資料
（Django 的 market 連線為唯讀，僅供讀取）。
"""

import sqlite3

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.market import selectors

client = APIClient()

_INSERT = (
    "INSERT INTO investor_conferences "
    "(market,code,announce_date,announce_time,name,subject,fact_date) "
    "VALUES (?,?,?,?,?,?,?)"
)


def _exec(db_file, rows: list[tuple]) -> None:
    """以獨立可寫 sqlite3 連線寫入假資料（非 Django 唯讀連線）。"""
    conn = sqlite3.connect(db_file)
    conn.executemany(_INSERT, rows)
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def _clear_cache():
    """每測試前後清快取，避免快取／節流狀態跨測試污染。"""
    cache.clear()
    yield
    cache.clear()


def test_empty_returns_200_empty_lists(market_db):
    """無資料 → 200，兩區塊回空清單。"""
    resp = client.get("/api/conferences/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["days"] == 30
    assert data["upcoming"] == []
    assert data["recent"] == []


def test_recent_returned_with_expected_fields(market_db):
    """近期公告回傳含指定欄位（market/code/name/subject/fact_date/announce_date）。"""
    _exec(market_db, [
        ("TWSE", "2330", "2026-07-17", "14:00:00", "台積電", "受邀參加法人說明會", "2026-08-01"),
    ])
    resp = client.get("/api/conferences/summary")
    assert resp.status_code == 200
    recent = resp.json()["recent"]
    assert len(recent) == 1
    row = recent[0]
    assert row["code"] == "2330"
    assert row["name"] == "台積電"
    assert row["announce_date"] == "2026-07-17"
    assert set(row) == {"market", "code", "name", "subject", "fact_date", "announce_date"}


def test_invalid_days_non_integer_400(market_db):
    """days 非整數 → 400 {"error": ...}。"""
    resp = client.get("/api/conferences/summary?days=abc")
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.parametrize("bad", ["0", "91", "-5"])
def test_days_out_of_range_400(market_db, bad):
    """days 超出 1~90 → 400 {"error": ...}。"""
    resp = client.get(f"/api/conferences/summary?days={bad}")
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.parametrize("ok", ["1", "90"])
def test_days_boundaries_ok(market_db, ok):
    """days 邊界 1 與 90 → 200。"""
    resp = client.get(f"/api/conferences/summary?days={ok}")
    assert resp.status_code == 200
    assert resp.json()["days"] == int(ok)


def test_cache_second_call_does_not_requery(market_db, monkeypatch):
    """第二次相同 days 呼叫命中快取，不再查 market 庫（selector 僅呼叫一次）。"""
    calls = {"n": 0}
    real = selectors.recent_conference_announcements

    def _counting(limit=20):
        calls["n"] += 1
        return real(limit)

    monkeypatch.setattr(
        "apps.market.selectors.recent_conference_announcements", _counting
    )

    first = client.get("/api/conferences/summary?days=30")
    second = client.get("/api/conferences/summary?days=30")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert calls["n"] == 1  # 第二次由快取回應


def test_cache_key_populated(market_db):
    """快取以 key conferences:{days} 存整包（前綴 swd:v1 由 CACHES 設定加上）。"""
    client.get("/api/conferences/summary?days=45")
    cached = cache.get("conferences:45")
    assert cached is not None
    assert cached["days"] == 45
