"""前復權 adjust_history 純函數單元測試（D10）。

公式與測試數字以姊妹專案 StockDCBot tests/test_analysis.py 的 AdjustHistoryTest 為權威，
逐案對齊：無事件／除息／除權／除權息／多事件疊加。純函數不進 DB，直接以 dict 序列驗證。
"""

from apps.market import services


def _hist(rows: list[tuple[str, float]]) -> list[dict]:
    # rows: (date, close)，開高低收一律用同值以簡化驗證（對齊 Bot 端 _hist）
    return [{"date": d, "open": c, "high": c, "low": c, "close": c} for d, c in rows]


def test_no_events_returns_unchanged_copy():
    """無事件：回傳未變更的複本（不動到輸入）。"""
    hist = _hist([("2026-06-03", 100.0), ("2026-06-01", 98.0)])
    out = services.adjust_history(hist, [])
    assert [r["close"] for r in out] == [100.0, 98.0]
    assert out[0] is not hist[0]  # 為複本
    assert hist[1]["close"] == 98.0


def test_cash_dividend_subtracts_before_ex_date_only():
    """除息：ex_date 之前每列減現金股利；當日與其後不動。"""
    hist = _hist([("2026-06-03", 100.0), ("2026-06-02", 100.0), ("2026-06-01", 100.0)])
    events = [{"ex_date": "2026-06-02", "cash_dividend": 2.0, "stock_ratio": 0.0}]
    out = services.adjust_history(hist, events)
    assert [r["close"] for r in out] == [100.0, 100.0, 98.0]


def test_stock_dividend_divides_by_ratio():
    """除權：ex_date 之前每列除以 (1+配股率)。"""
    hist = _hist([("2026-06-03", 110.0), ("2026-06-01", 110.0)])
    events = [{"ex_date": "2026-06-02", "cash_dividend": 0.0, "stock_ratio": 0.1}]
    out = services.adjust_history(hist, events)
    assert out[0]["close"] == 110.0  # 06-03 不動
    assert abs(out[1]["close"] - 100.0) < 1e-9  # 06-01: 110/1.1（浮點近似，對齊 Bot）


def test_combined_ex_rights_and_dividend():
    """除權息：先減現金股利再除配股率。"""
    hist = _hist([("2026-06-02", 100.0), ("2026-06-01", 100.0)])
    events = [{"ex_date": "2026-06-02", "cash_dividend": 1.0, "stock_ratio": 0.25}]
    out = services.adjust_history(hist, events)
    assert out[0]["close"] == 100.0
    assert out[1]["close"] == (100.0 - 1.0) / 1.25  # 79.2


def test_multiple_events_stack_newest_first():
    """多事件由新到舊疊加：Bot 端權威數字 78.4。"""
    hist = _hist([("2026-06-05", 100.0), ("2026-06-03", 100.0), ("2026-06-01", 100.0)])
    events = [
        {"ex_date": "2026-06-04", "cash_dividend": 2.0, "stock_ratio": 0.0},  # 較新
        {"ex_date": "2026-06-02", "cash_dividend": 0.0, "stock_ratio": 0.25},  # 較舊
    ]
    out = services.adjust_history(hist, events)
    assert out[0]["close"] == 100.0  # 06-05 無事件在其後
    assert out[1]["close"] == 98.0  # 06-03 僅受 06-04: 100-2
    assert abs(out[2]["close"] - 78.4) < 1e-9  # 06-01: (100-2)/1.25


def test_ohlc_all_adjusted_volume_untouched():
    """四價同步調整、量不調整（K 線副圖成交量需保留原值）。"""
    hist = [
        {"date": "2026-06-01", "open": 100.0, "high": 110.0, "low": 90.0,
         "close": 105.0, "volume": 5000.0}
    ]
    events = [{"ex_date": "2026-06-02", "cash_dividend": 5.0, "stock_ratio": 0.0}]
    out = services.adjust_history(hist, events)
    assert out[0]["open"] == 95.0
    assert out[0]["high"] == 105.0
    assert out[0]["low"] == 85.0
    assert out[0]["close"] == 100.0
    assert out[0]["volume"] == 5000.0  # 量不調整
