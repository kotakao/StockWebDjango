"""refresh_snapshot task 測試（CELERY_TASK_ALWAYS_EAGER）：冪等、快取失效、查無、重試。"""

import sqlite3

import pytest
from celery.exceptions import Retry
from django.core.cache import cache

from apps.stocks import tasks
from apps.stocks.models import StockSnapshot
from apps.stocks.tasks import refresh_snapshot

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
def test_upsert_idempotent(market_db_ready):
    """同 code+trade_date 重複執行僅一列（update_or_create 冪等）。"""
    _seed_quote(market_db_ready, "2330")

    assert refresh_snapshot.apply(args=["2330"]).get() == "updated"
    assert refresh_snapshot.apply(args=["2330"]).get() == "updated"

    qs = StockSnapshot.objects.filter(code="2330")
    assert qs.count() == 1
    assert str(qs.first().trade_date) == "2026-07-13"


@pytest.mark.django_db(transaction=True, databases=["default", "market"])
def test_cache_invalidated_after_write(market_db_ready):
    """寫入後主動失效 Redis swd:v1:stock:{code}。"""
    _seed_quote(market_db_ready, "2454")
    cache.set("stock:2454", {"stale": True}, timeout=600)

    refresh_snapshot.apply(args=["2454"]).get()

    assert cache.get("stock:2454") is None


@pytest.mark.django_db(transaction=True, databases=["default", "market"])
def test_code_not_found_no_write(market_db_ready):
    """查無代號：回 not_found、不寫入快照。"""
    result = refresh_snapshot.apply(args=["9999"]).get()

    assert result == "not_found"
    assert StockSnapshot.objects.filter(code="9999").count() == 0


@pytest.mark.django_db(transaction=True, databases=["default", "market"])
def test_retry_on_failure(market_db_ready, monkeypatch):
    """build_snapshot 失敗 → 觸發 self.retry（重試路徑；eager 模式下以 Retry 呈現）。"""
    calls = {"n": 0}

    def _boom(code):
        calls["n"] += 1
        raise RuntimeError("彙整失敗")

    monkeypatch.setattr(tasks, "build_snapshot", _boom)

    # eager＋EAGER_PROPAGATES：self.retry 以 celery Retry 呈現，證明重試已接上
    with pytest.raises(Retry):
        refresh_snapshot.apply(args=["2330"]).get()

    assert calls["n"] == 1
    assert refresh_snapshot.max_retries == 3
