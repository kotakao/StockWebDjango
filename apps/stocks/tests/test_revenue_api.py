"""GET /api/stocks/{code}/revenue API 測試（D9）：code 驗證 400、空清單 200、多月份輸出、快取。

以 conftest 的 market_db fixture 建暫時 SQLite market 庫，以可寫連線造假資料
（Django 的 market 連線唯讀，僅供讀取）。
"""

import sqlite3

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.market import selectors

client = APIClient()

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


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.parametrize("bad", ["12", "1234567", "abc$"])
def test_revenue_400_when_code_format_invalid(bad):
    """代號格式非 4-6 位英數 → 400 {"error": ...}（驗證先於 DB 查詢）。"""
    resp = client.get(f"/api/stocks/{bad}/revenue")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_revenue_200_empty_when_no_data(market_db):
    """格式正確但查無資料 → 200 空清單（不回 400）。"""
    resp = client.get("/api/stocks/2330/revenue")
    assert resp.status_code == 200
    assert resp.json() == {"code": "2330", "months": []}


def test_revenue_multi_month_newest_first(market_db):
    """多月份輸出，依 year_month 新到舊；NULL 欄位回 null。"""
    _exec(market_db, [
        ("TWSE", "2330", "2026-05", "台積電", 2000.0, 2.0, 20.0, 6000.0, 15.0),
        ("TWSE", "2330", "2026-06", "台積電", 3000.0, None, 30.0, 9000.0, None),
    ])

    resp = client.get("/api/stocks/2330/revenue")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "2330"
    assert [m["year_month"] for m in body["months"]] == ["2026-06", "2026-05"]
    assert body["months"][0]["mom_pct"] is None
    assert body["months"][0]["cum_yoy_pct"] is None
    assert body["months"][1]["revenue"] == 2000.0


def test_revenue_cache_second_call_does_not_requery(market_db, monkeypatch):
    """整包快取：第二次請求命中 stock:revenue:{code}，不再查 market 庫。"""
    _exec(market_db, [("TWSE", "2330", "2026-06", "台積電", 3000.0, 3.0, 30.0, 9000.0, 20.0)])

    calls = {"n": 0}
    real = selectors.monthly_revenue_rows

    def _counting(code):
        calls["n"] += 1
        return real(code)

    monkeypatch.setattr("apps.market.selectors.monthly_revenue_rows", _counting)

    first = client.get("/api/stocks/2330/revenue")
    second = client.get("/api/stocks/2330/revenue")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["n"] == 1
    assert cache.get("stock:revenue:2330") is not None
