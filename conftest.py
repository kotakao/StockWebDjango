"""pytest 共用 fixture。

market_db：建立「暫時 SQLite market 庫」並讓 Django 的 market 連線指向它。
schema 僅建測試所需表（對照 StockDCBot storage.py 的 CREATE TABLE）；
此 DDL 屬測試用暫時檔，不違反「正式程式嚴禁對 market 連線 DDL」鐵律（spec §4.2.4）。
"""

import sqlite3

import pytest
from django.db import connections

# 測試用 market schema：對照 StockDCBot storage.py，僅建 D0 測試所需表。
TEST_MARKET_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_quotes (
    market TEXT NOT NULL DEFAULT 'TWSE',
    date   TEXT NOT NULL,
    code   TEXT NOT NULL,
    name   TEXT,
    open   REAL,
    high   REAL,
    low    REAL,
    close  REAL,
    change REAL,
    volume REAL,
    PRIMARY KEY (market, date, code)
);

CREATE TABLE IF NOT EXISTS market_daily (
    market           TEXT NOT NULL DEFAULT 'TWSE',
    date             TEXT NOT NULL,
    index_close      REAL,
    index_change_pct REAL,
    turnover         REAL,
    up_count         REAL,
    down_count       REAL,
    foreign_net      REAL,
    trust_net        REAL,
    dealer_net       REAL,
    margin_balance   REAL,
    short_balance    REAL,
    PRIMARY KEY (market, date)
);
"""


@pytest.fixture
def market_db(tmp_path, django_db_blocker):
    """建立暫時 SQLite market 檔並將 Django market 連線指向它，測試結束後還原。

    直接解除 pytest-django 的 DB 封鎖（而非用 @django_db 標記），避免測試框架
    對唯讀的 market 連線嘗試建立/遷移測試庫而覆蓋本 fixture 注入的檔案。
    """
    db_file = tmp_path / "market.db"
    # 以獨立的可寫連線建 schema（非 Django 的 market 連線；後者為唯讀）
    conn = sqlite3.connect(db_file)
    conn.executescript(TEST_MARKET_SCHEMA)
    conn.commit()
    conn.close()

    market = connections["market"]
    market.close()
    old_name = market.settings_dict["NAME"]
    market.settings_dict["NAME"] = str(db_file)
    with django_db_blocker.unblock():
        try:
            yield db_file
        finally:
            market.close()
            market.settings_dict["NAME"] = old_name
