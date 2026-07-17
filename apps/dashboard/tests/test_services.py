"""dashboard services 單元測試（純邏輯，不進 DB）。

涵蓋：張換算（÷1000）、累積和序列、A/D Line、成交金額億元、缺欄容錯、空資料。
"""

from apps.dashboard.services import build_dashboard_summary


def _rows():
    """三列 market_daily（日期舊→新），刻意混入 None 以驗容錯。"""
    return [
        {
            "date": "2026-07-08",
            "index_close": 45000.0,
            "turnover": 150_000_000.0,  # 1.5 億
            "up_count": 10.0,
            "down_count": 4.0,
            "foreign_net": 1000.0,  # 1 張
            "trust_net": 2000.0,
            "dealer_net": -1000.0,
            "margin_balance": 600.0,
        },
        {
            "date": "2026-07-09",
            "index_close": 45100.0,
            "turnover": 300_000_000.0,  # 3.0 億
            "up_count": 5.0,
            "down_count": 8.0,
            "foreign_net": 2000.0,  # 2 張
            "trust_net": None,  # 缺值
            "dealer_net": 500.0,
            "margin_balance": None,  # 缺值
        },
        {
            "date": "2026-07-13",
            "index_close": None,  # 缺值
            "turnover": None,  # 缺值
            "up_count": None,  # 缺值
            "down_count": None,
            "foreign_net": None,  # 缺值
            "trust_net": 1000.0,
            "dealer_net": None,
            "margin_balance": 620.0,
        },
    ]


def test_dates_and_meta():
    """dates 保持舊→新順序，count/days 正確。"""
    out = build_dashboard_summary(_rows(), days=60)
    assert out["days"] == 60
    assert out["count"] == 3
    assert out["dates"] == ["2026-07-08", "2026-07-09", "2026-07-13"]


def test_institution_lots_and_cumsum():
    """三大法人：股→張（÷1000）後的累積和；缺值視為當日 0。"""
    out = build_dashboard_summary(_rows(), days=60)
    inst = out["institution"]
    # 外資 1000→1、2000→2、None→0 股；累積 [1, 3, 3]
    assert inst["foreign"] == [1.0, 3.0, 3.0]
    # 投信 2000→2、None→0、1000→1；累積 [2, 2, 3]
    assert inst["trust"] == [2.0, 2.0, 3.0]
    # 自營商 -1000→-1、500→0.5、None→0；累積 [-1, -0.5, -0.5]
    assert inst["dealer"] == [-1.0, -0.5, -0.5]


def test_breadth_counts_and_ad_line():
    """漲跌家數原始序列（缺值 None），A/D Line 為 (up-down) 累積。"""
    out = build_dashboard_summary(_rows(), days=60)
    breadth = out["breadth"]
    assert breadth["up"] == [10.0, 5.0, None]
    assert breadth["down"] == [4.0, 8.0, None]
    # (10-4)=6、(5-8)=-3、None→不變；累積 [6, 3, 3]
    assert breadth["ad_line"] == [6.0, 3.0, 3.0]


def test_index_turnover_to_100m():
    """指數收盤原始（缺值 None）；成交金額換算億元（÷1e8）。"""
    out = build_dashboard_summary(_rows(), days=60)
    index = out["index"]
    assert index["close"] == [45000.0, 45100.0, None]
    assert index["turnover_100m"] == [1.5, 3.0, None]


def test_margin_raw_with_nulls():
    """融資餘額原始序列，缺值以 None 帶出（不使整包失敗）。"""
    out = build_dashboard_summary(_rows(), days=60)
    assert out["margin"]["balance"] == [600.0, None, 620.0]


def test_empty_rows():
    """空資料：count 0、各序列為空 list，不拋例外。"""
    out = build_dashboard_summary([], days=30)
    assert out["count"] == 0
    assert out["dates"] == []
    assert out["institution"]["foreign"] == []
    assert out["breadth"]["ad_line"] == []
    assert out["index"]["close"] == []
    assert out["margin"]["balance"] == []
