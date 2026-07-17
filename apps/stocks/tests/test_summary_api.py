"""GET /api/stocks/{code}/summary API 測試：200／202／400 三分支與快取。"""

import sqlite3

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.stocks.models import StockSnapshot

client = APIClient()

_Q = "INSERT INTO daily_quotes (market,date,code,name,close) VALUES (?,?,?,?,?)"


def _seed_quote(db_file, code: str, date: str = "2026-07-13", close: float = 100.0):
    conn = sqlite3.connect(db_file)
    conn.execute(_Q, ("TWSE", date, code, "測試", close))
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db(transaction=True, databases=["default", "market"])
def test_summary_200_when_snapshot_current(market_db_ready):
    """快照存在且 trade_date == market 最新交易日 → 200，含 latest 與 recent 列表。"""
    _seed_quote(market_db_ready, "2330", date="2026-07-13")
    StockSnapshot.objects.create(code="2330", trade_date="2026-07-13", close=1050.0)

    resp = client.get("/api/stocks/2330/summary")

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "2330"
    assert data["latest"]["close"] == 1050.0
    assert data["latest"]["trade_date"] == "2026-07-13"
    assert len(data["recent"]) == 1
    # 快取以 key stock:{code} 存整包（前綴 swd:v1 由 CACHES 加上）
    assert cache.get("stock:2330") is not None


@pytest.mark.django_db(transaction=True, databases=["default", "market"])
def test_summary_202_when_stale_or_missing(market_db_ready):
    """代號存在但無最新快照 → enqueue 並回 202 {"status": "processing"}。"""
    _seed_quote(market_db_ready, "2454", date="2026-07-13")

    resp = client.get("/api/stocks/2454/summary")

    assert resp.status_code == 202
    assert resp.json() == {"status": "processing"}


@pytest.mark.django_db(transaction=True, databases=["default", "market"])
def test_summary_400_when_code_not_found(market_db_ready):
    """格式正確但查無代號 → 400 {"error": ...}。"""
    resp = client.get("/api/stocks/9999/summary")

    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.parametrize("bad", ["12", "1234567", "abc$"])
def test_summary_400_when_code_format_invalid(bad):
    """代號格式非 4-6 位英數 → 400（驗證先於任何 DB 查詢）。"""
    resp = client.get(f"/api/stocks/{bad}/summary")

    assert resp.status_code == 400
    assert "error" in resp.json()
