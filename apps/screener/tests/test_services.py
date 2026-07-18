"""screen 純函數單元測試（D8）：衍生欄計算、各條件獨立與複合、None 排除、上限 200 與 total。

純函數不碰 DB，直接以 dict 列表為輸入。
"""

from apps.screener.services import screen


def _row(code, close=100.0, change=5.0, volume=1_000_000, pe=15.0, pb=2.0, yld=3.0):
    """組一列基底行情（含估值），欄位對齊 quotes_with_valuation 輸出。"""
    return {
        "market": "TWSE",
        "code": code,
        "name": f"股{code}",
        "close": close,
        "change": change,
        "volume": volume,
        "pe": pe,
        "pb": pb,
        "dividend_yield": yld,
    }


def test_change_pct_and_volume_lots_derived():
    """衍生欄：change_pct＝change/(close-change)*100、volume_lots＝volume/1000。"""
    out = screen([_row("1001", close=105.0, change=5.0, volume=1_234_000)], {"pe_min": 0})
    r = out["results"][0]
    assert r["change_pct"] == 5.0  # 5/(105-5)*100
    assert r["volume_lots"] == 1234.0


def test_change_pct_none_when_prev_close_zero():
    """前收（close-change）為 0 → change_pct 為 None，開此條件時被排除。"""
    rows = [_row("1001", close=5.0, change=5.0)]  # 前收＝0
    out = screen(rows, {"change_pct_min": -100})
    assert out["total"] == 0


def test_change_pct_none_when_close_or_change_missing():
    """close 或 change 缺值 → change_pct 為 None。"""
    out = screen([_row("1001", close=None), _row("1002", change=None)], {"pe_min": 0})
    assert all(r["change_pct"] is None for r in out["results"])


def test_volume_lots_none_when_volume_missing():
    """volume 為 None → volume_lots 為 None。"""
    out = screen([_row("1001", volume=None)], {"pe_min": 0})
    assert out["results"][0]["volume_lots"] is None


def test_pe_min_max():
    """pe_min/pe_max 各自過濾（含邊界）。"""
    rows = [_row("1001", pe=10.0), _row("1002", pe=20.0), _row("1003", pe=30.0)]
    assert [r["code"] for r in screen(rows, {"pe_min": 20})["results"]] == ["1002", "1003"]
    assert [r["code"] for r in screen(rows, {"pe_max": 20})["results"]] == ["1001", "1002"]


def test_pb_and_yield_and_volume_filters():
    """pb_min/pb_max、yield_min、volume_lots_min 各自過濾。"""
    rows = [
        _row("1001", pb=1.0, yld=2.0, volume=500_000),
        _row("1002", pb=3.0, yld=5.0, volume=2_000_000),
    ]
    assert [r["code"] for r in screen(rows, {"pb_min": 2})["results"]] == ["1002"]
    assert [r["code"] for r in screen(rows, {"pb_max": 2})["results"]] == ["1001"]
    assert [r["code"] for r in screen(rows, {"yield_min": 3})["results"]] == ["1002"]
    assert [r["code"] for r in screen(rows, {"volume_lots_min": 1000})["results"]] == ["1002"]


def test_change_pct_min_max():
    """change_pct_min/change_pct_max 過濾（前收＝close-change）。"""
    rows = [
        _row("1001", close=110.0, change=10.0),  # +10%
        _row("1002", close=95.0, change=-5.0),   # -5%
    ]
    assert [r["code"] for r in screen(rows, {"change_pct_min": 0})["results"]] == ["1001"]
    assert [r["code"] for r in screen(rows, {"change_pct_max": 0})["results"]] == ["1002"]


def test_composite_filters():
    """複合條件：需同時滿足全部開啟的條件。"""
    rows = [
        _row("1001", pe=10.0, yld=5.0),
        _row("1002", pe=10.0, yld=1.0),
        _row("1003", pe=40.0, yld=5.0),
    ]
    out = screen(rows, {"pe_max": 20, "yield_min": 3})
    assert [r["code"] for r in out["results"]] == ["1001"]


def test_none_column_excluded_only_when_condition_on():
    """該欄為 None 的列僅在開對應條件時被排除；未開時保留。"""
    rows = [_row("1001", pe=None)]
    assert screen(rows, {"pe_min": 0})["total"] == 0  # 開 pe 條件 → 排除
    assert screen(rows, {"pb_min": 0})["total"] == 1  # 未開 pe 條件 → 保留


def test_sorted_by_code():
    """結果依 code 排序。"""
    rows = [_row("1003"), _row("1001"), _row("1002")]
    assert [r["code"] for r in screen(rows, {"pe_min": 0})["results"]] == ["1001", "1002", "1003"]


def test_limit_200_but_total_counts_all():
    """符合 250 檔 → results 上限 200，total 為 250。"""
    rows = [_row(f"{i:04d}") for i in range(250)]
    out = screen(rows, {"pe_min": 0})
    assert out["total"] == 250
    assert len(out["results"]) == 200
    # 前 200（依 code 排序）為 0000~0199
    assert out["results"][0]["code"] == "0000"
    assert out["results"][-1]["code"] == "0199"
