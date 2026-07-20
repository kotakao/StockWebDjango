"""GET /api/stocks/{code}/quotes API 測試（D10）：參數驗證/400 分支/序列/快取。

以 conftest 的 market_db fixture 建暫時 SQLite market 庫，以可寫連線造假資料。
"""

import sqlite3

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.stocks import services

client = APIClient()

_Q = (
    "INSERT INTO daily_quotes (market,date,code,name,open,high,low,close,change,volume) "
    "VALUES (?,?,?,?,?,?,?,?,?,?)"
)
_I = (
    "INSERT INTO institutional (market,date,code,name,foreign_net,trust_net,dealer_net) "
    "VALUES (?,?,?,?,?,?,?)"
)


def _seed(db_file, quotes=(), inst=()):
    conn = sqlite3.connect(db_file)
    if quotes:
        conn.executemany(_Q, quotes)
    if inst:
        conn.executemany(_I, inst)
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.parametrize("bad", ["12", "1234567", "abc$"])
def test_quotes_400_when_code_format_invalid(bad):
    """代號格式非 4-6 位英數 → 400（驗證先於 DB 查詢）。"""
    resp = client.get(f"/api/stocks/{bad}/quotes")
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.parametrize("bad", ["0", "253", "-1", "abc", "1.5"])
def test_quotes_400_when_days_invalid(bad):
    """days 非 1~252 整數 → 400。"""
    resp = client.get(f"/api/stocks/2330/quotes?days={bad}")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_quotes_400_when_code_not_found(market_db):
    """格式正確但 daily_quotes 查無代號 → 400。"""
    resp = client.get("/api/stocks/2330/quotes")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_quotes_defaults_and_series(market_db):
    """預設 days=252、adjusted=true；回傳日期舊到新序列與法人淨額。"""
    _seed(
        market_db,
        quotes=[
            ("TWSE", "2026-06-01", "2330", "台積電", 100.0, 101.0, 99.0, 100.0, 0.0, 5000.0),
            ("TWSE", "2026-06-02", "2330", "台積電", 100.0, 102.0, 100.0, 101.0, 1.0, 6000.0),
        ],
        inst=[("TWSE", "2026-06-02", "2330", "台積電", 2_000_000.0, 0.0, 0.0)],
    )

    resp = client.get("/api/stocks/2330/quotes")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "2330"
    assert body["days"] == 252
    assert body["adjusted"] is True
    assert [q["date"] for q in body["quotes"]] == ["2026-06-01", "2026-06-02"]
    assert body["quotes"][0]["inst_net"] is None
    assert body["quotes"][1]["inst_net"] == 2000


def test_quotes_adjusted_false_param(market_db):
    """adjusted=false → 未還原，且回應標記 adjusted False。"""
    _seed(
        market_db,
        quotes=[("TWSE", "2026-06-01", "2330", "台積電", 100.0, 101.0, 99.0, 100.0, 0.0, 5000.0)],
    )
    resp = client.get("/api/stocks/2330/quotes?adjusted=false")
    assert resp.status_code == 200
    assert resp.json()["adjusted"] is False


def test_quotes_cache_second_call_does_not_requery(market_db, monkeypatch):
    """整包快取：第二次請求命中 quotes:{code}:{days}:{adjusted}，不再組裝序列。"""
    _seed(
        market_db,
        quotes=[("TWSE", "2026-06-01", "2330", "台積電", 100.0, 101.0, 99.0, 100.0, 0.0, 5000.0)],
    )

    calls = {"n": 0}
    real = services.build_quotes

    def _counting(code, days, adjusted):
        calls["n"] += 1
        return real(code, days, adjusted)

    monkeypatch.setattr("apps.stocks.views.services.build_quotes", _counting)

    first = client.get("/api/stocks/2330/quotes?days=60&adjusted=true")
    second = client.get("/api/stocks/2330/quotes?days=60&adjusted=true")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["n"] == 1
    assert cache.get("quotes:2330:60:true") is not None
