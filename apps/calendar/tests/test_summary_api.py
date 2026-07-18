"""GET /api/calendar/summary API 測試：month 驗證、預設當月、空清單、序列輸出、Redis 快取。

以 conftest 的 market_db fixture 建暫時 SQLite market 庫，直接以可寫連線造假資料
（Django 的 market 連線為唯讀，僅供讀取）。
"""

import sqlite3
from datetime import date

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.market import selectors

client = APIClient()

_DIV_INSERT = (
    "INSERT INTO dividend_events "
    "(market,code,ex_date,name,event_type,cash_dividend,stock_ratio) VALUES (?,?,?,?,?,?,?)"
)


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


def test_empty_returns_200_empty_lists(market_db):
    """無資料 → 200，兩區塊回空清單，month 為當月。"""
    resp = client.get("/api/calendar/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["month"] == date.today().strftime("%Y-%m")
    assert data["dividends"] == []
    assert data["conferences"] == []


def test_dividends_returned_with_expected_fields(market_db):
    """除權息回傳含指定欄位；僅落在該月者入列。"""
    _exec(market_db, _DIV_INSERT, [
        ("TWSE", "2330", "2026-08-15", "台積電", "現金股利", 15.0, None),
        ("TWSE", "2454", "2026-09-01", "聯發科", "現金股利", 20.0, None),  # 次月不入
    ])
    resp = client.get("/api/calendar/summary?month=2026-08")
    assert resp.status_code == 200
    dividends = resp.json()["dividends"]
    assert len(dividends) == 1
    row = dividends[0]
    assert row["code"] == "2330"
    assert row["ex_date"] == "2026-08-15"
    assert set(row) == {
        "market", "code", "name", "event_type", "ex_date", "cash_dividend", "stock_ratio",
    }


@pytest.mark.parametrize("bad", ["2026-13", "2026/07", "abc", "2026-07-15", "2026-7"])
def test_invalid_month_format_400(market_db, bad):
    """month 格式不符 → 400 {"error": ...}。"""
    resp = client.get(f"/api/calendar/summary?month={bad}")
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.parametrize("bad", ["2019-12", "2100-01"])
def test_month_year_out_of_range_400(market_db, bad):
    """month 年份超出 2020~2099 → 400 {"error": ...}。"""
    resp = client.get(f"/api/calendar/summary?month={bad}")
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.parametrize("ok", ["2020-01", "2099-12"])
def test_month_boundaries_ok(market_db, ok):
    """month 邊界 2020-01 與 2099-12 → 200。"""
    resp = client.get(f"/api/calendar/summary?month={ok}")
    assert resp.status_code == 200
    assert resp.json()["month"] == ok


def test_cache_second_call_does_not_requery(market_db, monkeypatch):
    """第二次相同 month 呼叫命中快取，不再查 market 庫（selector 僅呼叫一次）。"""
    calls = {"n": 0}
    real = selectors.dividend_events_between

    def _counting(start, end):
        calls["n"] += 1
        return real(start, end)

    monkeypatch.setattr("apps.market.selectors.dividend_events_between", _counting)

    first = client.get("/api/calendar/summary?month=2026-08")
    second = client.get("/api/calendar/summary?month=2026-08")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert calls["n"] == 1


def test_cache_key_populated(market_db):
    """快取以 key calendar:{month} 存整包（前綴 swd:v1 由 CACHES 設定加上）。"""
    client.get("/api/calendar/summary?month=2026-08")
    cached = cache.get("calendar:2026-08")
    assert cached is not None
    assert cached["month"] == "2026-08"
