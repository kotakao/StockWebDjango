"""build_peers 同業對比組裝單元測試（D11）：is_self 標記、缺值容錯、單一成員、表不存在。

以 conftest 的 market_db fixture 建暫時 SQLite market 庫，以可寫連線造假資料
（Django 的 market 連線唯讀，僅供讀取）。
"""

import sqlite3

from django.db import connections

from apps.stocks import services

_P = (
    "INSERT INTO company_profile "
    "(market,code,name,abbreviation,en_abbreviation,industry_code,listing_date,report_date) "
    "VALUES (?,?,?,?,?,?,?,?)"
)
_V = "INSERT INTO valuation (market,date,code,pe,dividend_yield,pb) VALUES (?,?,?,?,?,?)"
_R = (
    "INSERT INTO monthly_revenue "
    "(market,code,year_month,name,revenue,mom_pct,yoy_pct,cum_revenue,cum_yoy_pct) "
    "VALUES (?,?,?,?,?,?,?,?,?)"
)
_F = (
    "INSERT INTO quarterly_financials "
    "(market,code,year_quarter,name,revenue,gross_profit,operating_income,net_income,eps) "
    "VALUES (?,?,?,?,?,?,?,?,?)"
)


def _seed(db_file, profiles=(), vals=(), revs=(), fins=()):
    conn = sqlite3.connect(db_file)
    if profiles:
        conn.executemany(_P, profiles)
    if vals:
        conn.executemany(_V, vals)
    if revs:
        conn.executemany(_R, revs)
    if fins:
        conn.executemany(_F, fins)
    conn.commit()
    conn.close()


def test_assembles_peers_with_self_flag(market_db):
    """同 industry_code 全部個股入列（依 code 排序），本股標 is_self；比率讀取端計算。"""
    _seed(
        market_db,
        profiles=[
            ("TWSE", "2330", "台積電", "台積電", "TSMC", "24", "1994-09-05", None),
            ("TWSE", "2454", "聯發科", "聯發科", "MTK", "24", "2001-07-23", None),
            ("TWSE", "3008", "大立光", "大立光", "LARGAN", "30", None, None),
        ],
        vals=[
            ("TWSE", "2026-07-13", "2330", 20.0, 2.0, 5.0),
            ("TWSE", "2026-07-13", "2454", 15.0, 3.0, 4.0),
        ],
        revs=[
            ("TWSE", "2330", "2026-06", "台積電", 3000.0, 3.0, 30.0, 9000.0, 20.0),
            ("TWSE", "2454", "2026-06", "聯發科", 500.0, 1.0, 10.0, 1500.0, 8.0),
        ],
        fins=[
            ("TWSE", "2330", "2026Q1", "台積電", 1000.0, 600.0, 400.0, 300.0, 8.0),
            ("TWSE", "2454", "2026Q1", "聯發科", 500.0, 250.0, 100.0, 80.0, 5.0),
        ],
    )

    result = services.build_peers("2330")

    assert result["reason"] is None
    peers = result["peers"]
    # 僅同 industry 24（2330、2454）依 code 排序入列；3008（industry 30）不入
    assert [p["code"] for p in peers] == ["2330", "2454"]
    self_row = peers[0]
    assert self_row["is_self"] is True
    assert self_row["name"] == "台積電"
    assert self_row["pe"] == 20.0
    assert self_row["pb"] == 5.0
    assert self_row["dividend_yield"] == 2.0
    assert self_row["revenue_yoy"] == 30.0
    assert self_row["gross_margin"] == 60.0  # 600/1000*100
    assert peers[1]["is_self"] is False
    assert peers[1]["gross_margin"] == 50.0  # 250/500*100


def test_missing_values_tolerated(market_db):
    """同業成員缺 valuation/revenue/financials 時各欄回 None；毛利率分母 0 亦回 None。"""
    _seed(
        market_db,
        profiles=[
            ("TWSE", "1101", "甲公司", None, None, "01", None, None),
            ("TWSE", "1102", "乙公司", None, None, "01", None, None),
        ],
        vals=[("TWSE", "2026-07-13", "1101", 10.0, 1.0, 2.0)],
        revs=[("TWSE", "1101", "2026-06", "甲公司", 100.0, 1.0, 5.0, 300.0, 4.0)],
        # 1101 revenue=0 → 毛利率分母 0 容錯 None；1102 完全無估值/營收/財報
        fins=[("TWSE", "1101", "2026Q1", "甲公司", 0.0, 50.0, 10.0, 5.0, 1.0)],
    )

    peers = {p["code"]: p for p in services.build_peers("1101")["peers"]}

    assert peers["1101"]["pe"] == 10.0
    assert peers["1101"]["gross_margin"] is None  # revenue=0 → 分母 0
    assert peers["1102"]["pe"] is None
    assert peers["1102"]["pb"] is None
    assert peers["1102"]["dividend_yield"] is None
    assert peers["1102"]["revenue_yoy"] is None
    assert peers["1102"]["gross_margin"] is None
    assert peers["1102"]["name"] == "乙公司"


def test_single_member_industry(market_db):
    """產業僅本股一家 → peers 只含本股一列，is_self True。"""
    _seed(
        market_db,
        profiles=[("TWSE", "9999", "獨行俠", None, None, "88", None, None)],
    )

    result = services.build_peers("9999")

    assert result["reason"] is None
    assert len(result["peers"]) == 1
    assert result["peers"][0]["code"] == "9999"
    assert result["peers"][0]["is_self"] is True


def test_no_industry_data_returns_reason(market_db):
    """該股 industry_code 為 NULL 或不在 company_profile → peers 空、附 reason。"""
    _seed(
        market_db,
        profiles=[("TWSE", "5555", "無產業", None, None, None, None, None)],
    )

    # industry_code 為 NULL
    result = services.build_peers("5555")
    assert result["peers"] == []
    assert result["reason"]

    # 完全不在 company_profile
    result2 = services.build_peers("7777")
    assert result2["peers"] == []
    assert result2["reason"]


def test_table_missing_returns_reason(market_db):
    """company_profile 表不存在 → peers 空、附缺表 reason（不拋錯）。"""
    conn = sqlite3.connect(market_db)
    conn.execute("DROP TABLE company_profile")
    conn.commit()
    conn.close()
    connections["market"].close()  # 強制以現況（無此表）重連

    result = services.build_peers("2330")

    assert result["peers"] == []
    assert result["reason"]
