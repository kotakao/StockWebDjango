"""鐵律證明測試：對 market 連線的寫入必須失敗（spec §4.2 / §9）。

雙保險之連線層：PRAGMA query_only=ON 使任何 DDL/DML 回 readonly database 錯誤。
"""

import pytest
from django.db import connections
from django.db.utils import OperationalError


def test_market_read_succeeds(market_db):
    """唯讀連線可正常讀取（SELECT）。"""
    with connections["market"].cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM market_daily")
        assert cursor.fetchone()[0] == 0


def test_market_insert_fails(market_db):
    """INSERT 寫入必須失敗（readonly database）。"""
    with pytest.raises(OperationalError) as exc:
        with connections["market"].cursor() as cursor:
            cursor.execute(
                "INSERT INTO market_daily (market, date, index_close) VALUES (?, ?, ?)",
                ("TWSE", "2024-01-02", 100.0),
            )
    assert "readonly" in str(exc.value).lower()


def test_market_ddl_fails(market_db):
    """CREATE TABLE（DDL）必須失敗（readonly database）。"""
    with pytest.raises(OperationalError) as exc:
        with connections["market"].cursor() as cursor:
            cursor.execute("CREATE TABLE should_not_exist (x INTEGER)")
    assert "readonly" in str(exc.value).lower()
