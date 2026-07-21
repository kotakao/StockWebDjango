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

CREATE TABLE IF NOT EXISTS valuation (
    market         TEXT NOT NULL DEFAULT 'TWSE',
    date           TEXT NOT NULL,
    code           TEXT NOT NULL,
    pe             REAL,
    dividend_yield REAL,
    pb             REAL,
    PRIMARY KEY (market, date, code)
);

CREATE TABLE IF NOT EXISTS institutional (
    market      TEXT NOT NULL DEFAULT 'TWSE',
    date        TEXT NOT NULL,
    code        TEXT NOT NULL,
    name        TEXT,
    foreign_net REAL,
    trust_net   REAL,
    dealer_net  REAL,
    PRIMARY KEY (market, date, code)
);

CREATE TABLE IF NOT EXISTS monthly_revenue (
    market      TEXT NOT NULL DEFAULT 'TWSE',
    code        TEXT NOT NULL,
    year_month  TEXT NOT NULL,
    name        TEXT,
    revenue     REAL,
    mom_pct     REAL,
    yoy_pct     REAL,
    cum_revenue REAL,
    cum_yoy_pct REAL,
    PRIMARY KEY (market, code, year_month)
);

CREATE TABLE IF NOT EXISTS quarterly_financials (
    market           TEXT NOT NULL DEFAULT 'TWSE',
    code             TEXT NOT NULL,
    year_quarter     TEXT NOT NULL,
    name             TEXT,
    revenue          REAL,
    gross_profit     REAL,
    operating_income REAL,
    net_income       REAL,
    eps              REAL,
    PRIMARY KEY (market, code, year_quarter)
);

CREATE TABLE IF NOT EXISTS watchlist (
    user_id TEXT NOT NULL,
    code    TEXT NOT NULL,
    PRIMARY KEY (user_id, code)
);

CREATE TABLE IF NOT EXISTS holdings (
    user_id    TEXT NOT NULL,
    code       TEXT NOT NULL,
    shares     REAL,
    avg_cost   REAL,
    updated_at TEXT,
    PRIMARY KEY (user_id, code)
);

CREATE TABLE IF NOT EXISTS dividend_events (
    market        TEXT NOT NULL DEFAULT 'TWSE',
    code          TEXT NOT NULL,
    ex_date       TEXT NOT NULL,
    name          TEXT,
    event_type    TEXT,
    cash_dividend REAL,
    stock_ratio   REAL,
    PRIMARY KEY (market, code, ex_date)
);

CREATE TABLE IF NOT EXISTS investor_conferences (
    market         TEXT NOT NULL DEFAULT 'TWSE',
    code           TEXT NOT NULL,
    announce_date  TEXT NOT NULL,
    announce_time  TEXT NOT NULL,
    name           TEXT,
    subject        TEXT,
    matched_clause TEXT,
    fact_date      TEXT,
    description    TEXT,
    report_date    TEXT,
    PRIMARY KEY (market, code, announce_date, announce_time)
);

CREATE TABLE IF NOT EXISTS company_profile (
    market          TEXT NOT NULL DEFAULT 'TWSE',
    code            TEXT NOT NULL,
    name            TEXT,
    abbreviation    TEXT,
    en_abbreviation TEXT,
    industry_code   TEXT,
    listing_date    TEXT,
    report_date     TEXT,
    PRIMARY KEY (market, code)
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


@pytest.fixture
def market_db_ready(market_db):
    """market_db 的變體：供同時存取 default 庫的測試使用。

    當測試以 @pytest.mark.django_db(transaction=True, databases=["default", "market"])
    同時管理 default 與 market 連線時，pytest-django 會先以「測試前既有連線」開啟 market，
    使 market_db 注入的 NAME 未套用到既有連線。此處於 market_db 之後再關閉 market 連線，
    強制後續查詢以 tmp 檔重連。需搭配 transaction=True（atomic 模式下連線不可關閉）。
    """
    connections["market"].close()
    return market_db
