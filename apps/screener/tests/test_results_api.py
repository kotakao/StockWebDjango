"""GET /api/screener/results API 測試（D8）：無條件/非數值 400、快取行為、無資料 200、結果欄位。

以 conftest 的 market_db fixture 建暫時 SQLite market 庫，以可寫連線造假資料
（Django 的 market 連線為唯讀，僅供讀取）。
"""

import sqlite3

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.market import selectors

client = APIClient()

_Q = "INSERT INTO daily_quotes (market,date,code,name,close,change,volume) VALUES (?,?,?,?,?,?,?)"
_V = "INSERT INTO valuation (market,date,code,pe,dividend_yield,pb) VALUES (?,?,?,?,?,?)"


def _exec(db_file, sql, rows):
    conn = sqlite3.connect(db_file)
    conn.executemany(sql, rows)
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_no_condition_returns_400(market_db):
    """未帶任何條件 → 400 與固定訊息。"""
    resp = client.get("/api/screener/results")
    assert resp.status_code == 400
    assert resp.json()["error"] == "至少需指定一個篩選條件"


def test_non_numeric_condition_returns_400(market_db):
    """條件值非數值 → 400 {"error": ...}。"""
    resp = client.get("/api/screener/results?pe_min=abc")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_empty_data_returns_200(market_db):
    """daily_quotes 無任何資料（帶條件）→ 200，date 為 null、空結果。"""
    resp = client.get("/api/screener/results?pe_min=0")
    assert resp.status_code == 200
    assert resp.json() == {"date": None, "total": 0, "results": []}


def test_results_shape_and_filter(market_db):
    """回傳最新交易日與符合列；每列含指定欄位、數值容錯 null。"""
    _exec(market_db, _Q, [
        ("TWSE", "2026-07-17", "2330", "台積電", 1000.0, 10.0, 5_000_000),
        ("TWSE", "2026-07-17", "1111", "低估值", 50.0, 1.0, 100_000),
    ])
    _exec(market_db, _V, [("TWSE", "2026-07-17", "2330", 18.5, 2.1, 5.6)])

    resp = client.get("/api/screener/results?pe_min=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == "2026-07-17"
    assert body["total"] == 1
    row = body["results"][0]
    assert row["code"] == "2330"
    assert set(row) == {
        "market", "code", "name", "close", "change_pct",
        "pe", "pb", "dividend_yield", "volume_lots",
    }
    assert row["pe"] == 18.5
    assert row["volume_lots"] == 5000.0


def test_base_cache_second_call_does_not_requery(market_db, monkeypatch):
    """基底快取：第二次請求命中 screener:base:{date}，不再查 market 庫（selector 僅呼叫一次）。"""
    _exec(market_db, _Q, [("TWSE", "2026-07-17", "2330", "台積電", 1000.0, 10.0, 5_000_000)])

    calls = {"n": 0}
    real = selectors.quotes_with_valuation

    def _counting(quote_date):
        calls["n"] += 1
        return real(quote_date)

    monkeypatch.setattr("apps.market.selectors.quotes_with_valuation", _counting)

    first = client.get("/api/screener/results?pe_min=0")
    second = client.get("/api/screener/results?pe_min=0")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["n"] == 1
    assert cache.get("screener:base:2026-07-17") is not None
