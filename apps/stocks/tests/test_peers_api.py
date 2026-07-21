"""GET /api/stocks/{code}/peers API 測試（D11）：code 驗證 400、查無代號 400、
200 同業對比、缺表/無產業資料 200 reason、快取。

以 conftest 的 market_db fixture 建暫時 SQLite market 庫，以可寫連線造假資料
（Django 的 market 連線唯讀，僅供讀取）。
"""

import sqlite3

import pytest
from django.core.cache import cache
from django.db import connections
from rest_framework.test import APIClient

from apps.stocks import services

client = APIClient()

_Q = (
    "INSERT INTO daily_quotes (market,date,code,name,open,high,low,close,change,volume) "
    "VALUES (?,?,?,?,?,?,?,?,?,?)"
)
_P = (
    "INSERT INTO company_profile "
    "(market,code,name,abbreviation,en_abbreviation,industry_code,listing_date,report_date) "
    "VALUES (?,?,?,?,?,?,?,?)"
)
_V = "INSERT INTO valuation (market,date,code,pe,dividend_yield,pb) VALUES (?,?,?,?,?,?)"


def _seed(db_file, quotes=(), profiles=(), vals=()):
    conn = sqlite3.connect(db_file)
    if quotes:
        conn.executemany(_Q, quotes)
    if profiles:
        conn.executemany(_P, profiles)
    if vals:
        conn.executemany(_V, vals)
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.parametrize("bad", ["12", "1234567", "abc$"])
def test_peers_400_when_code_format_invalid(bad):
    """代號格式非 4-6 位英數 → 400 {"error": ...}（驗證先於 DB 查詢）。"""
    resp = client.get(f"/api/stocks/{bad}/peers")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_peers_400_when_code_not_found(market_db):
    """格式正確但 daily_quotes 查無代號 → 400。"""
    resp = client.get("/api/stocks/2330/peers")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_peers_200_with_peers(market_db):
    """代號存在且有同業 → 200，回同業對比列，本股標 is_self。"""
    _seed(
        market_db,
        quotes=[("TWSE", "2026-07-13", "2330", "台積電", 1.0, 1.0, 1.0, 1000.0, 0.0, 1.0)],
        profiles=[
            ("TWSE", "2330", "台積電", None, None, "24", None, None),
            ("TWSE", "2454", "聯發科", None, None, "24", None, None),
        ],
        vals=[("TWSE", "2026-07-13", "2330", 20.0, 2.0, 5.0)],
    )

    resp = client.get("/api/stocks/2330/peers")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "2330"
    assert body["reason"] is None
    assert [p["code"] for p in body["peers"]] == ["2330", "2454"]
    self_row = next(p for p in body["peers"] if p["code"] == "2330")
    assert self_row["is_self"] is True
    assert self_row["pe"] == 20.0


def test_peers_200_reason_when_no_industry(market_db):
    """代號存在但無產業分類（industry_code NULL）→ 200 空清單附 reason。"""
    _seed(
        market_db,
        quotes=[("TWSE", "2026-07-13", "2330", "台積電", 1.0, 1.0, 1.0, 1000.0, 0.0, 1.0)],
        profiles=[("TWSE", "2330", "台積電", None, None, None, None, None)],
    )

    resp = client.get("/api/stocks/2330/peers")

    assert resp.status_code == 200
    body = resp.json()
    assert body["peers"] == []
    assert body["reason"]


def test_peers_200_reason_when_table_missing(market_db):
    """company_profile 表不存在 → 200 空清單附缺表 reason（不回 500）。"""
    _seed(
        market_db,
        quotes=[("TWSE", "2026-07-13", "2330", "台積電", 1.0, 1.0, 1.0, 1000.0, 0.0, 1.0)],
    )
    conn = sqlite3.connect(market_db)
    conn.execute("DROP TABLE company_profile")
    conn.commit()
    conn.close()
    connections["market"].close()  # 強制以現況（無此表）重連

    resp = client.get("/api/stocks/2330/peers")

    assert resp.status_code == 200
    body = resp.json()
    assert body["peers"] == []
    assert body["reason"]


def test_peers_cache_second_call_does_not_requery(market_db, monkeypatch):
    """整包快取：第二次請求命中 peers:{code}，不再組裝同業。"""
    _seed(
        market_db,
        quotes=[("TWSE", "2026-07-13", "2330", "台積電", 1.0, 1.0, 1.0, 1000.0, 0.0, 1.0)],
        profiles=[("TWSE", "2330", "台積電", None, None, "24", None, None)],
    )

    calls = {"n": 0}
    real = services.build_peers

    def _counting(code):
        calls["n"] += 1
        return real(code)

    monkeypatch.setattr("apps.stocks.views.services.build_peers", _counting)

    first = client.get("/api/stocks/2330/peers")
    second = client.get("/api/stocks/2330/peers")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["n"] == 1
    assert cache.get("peers:2330") is not None
