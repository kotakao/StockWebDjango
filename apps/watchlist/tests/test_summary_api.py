"""GET /api/watchlist/summary API 測試：空清單、序列輸出、Redis 快取行為。

以 conftest 的 market_db fixture 建暫時 SQLite market 庫，直接以可寫連線造假資料
（Django 的 market 連線為唯讀，僅供讀取）。user_id 取自 settings.WATCHLIST_USER_ID（預設 "0"）。
"""

import sqlite3

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.watchlist import services

client = APIClient()


def _exec(db_file, sql: str, rows: list[tuple]) -> None:
    """以獨立可寫 sqlite3 連線寫入假資料（非 Django 唯讀連線）。"""
    conn = sqlite3.connect(db_file)
    conn.executemany(sql, rows)
    conn.commit()
    conn.close()


_Q = "INSERT INTO daily_quotes (market,date,code,name,close) VALUES (?,?,?,?,?)"
_W = "INSERT INTO watchlist (user_id,code) VALUES (?,?)"


@pytest.fixture(autouse=True)
def _clear_cache():
    """每測試前後清快取，避免快取／節流狀態跨測試污染。"""
    cache.clear()
    yield
    cache.clear()


def test_empty_returns_200_empty_lists(market_db):
    """watchlist/holdings 皆空 → 200，兩區塊回空清單。"""
    resp = client.get("/api/watchlist/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["watchlist"] == []
    assert data["holdings"] == []


def test_watchlist_returned(market_db):
    """自選股回傳含最新收盤。"""
    _exec(market_db, _Q, [("TWSE", "2026-07-13", "2330", "台積電", 1050.0)])
    _exec(market_db, _W, [("0", "2330")])

    resp = client.get("/api/watchlist/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["watchlist"]) == 1
    assert data["watchlist"][0]["code"] == "2330"
    assert data["watchlist"][0]["close"] == 1050.0


def test_cache_second_call_does_not_rebuild(market_db, monkeypatch):
    """第二次呼叫命中快取，不再重建（service 僅呼叫一次）。"""
    _exec(market_db, _W, [("0", "2330")])
    calls = {"n": 0}
    real = services.build_watchlist_summary

    def _counting(user_id):
        calls["n"] += 1
        return real(user_id)

    monkeypatch.setattr(
        "apps.watchlist.views.build_watchlist_summary", _counting
    )

    first = client.get("/api/watchlist/summary")
    second = client.get("/api/watchlist/summary")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert calls["n"] == 1  # 第二次由快取回應


def test_cache_key_populated(market_db):
    """快取以 key watchlist:{user_id} 存整包（前綴 swd:v1 由 CACHES 設定加上）。"""
    client.get("/api/watchlist/summary")
    cached = cache.get("watchlist:0")
    assert cached is not None
    assert cached["user_id"] == "0"
