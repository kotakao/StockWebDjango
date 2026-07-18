"""screener 純商業邏輯（spec §3.2）：對基底行情列做衍生欄計算與複合條件篩選。

不碰 HTTP、不碰 DB；輸入為 quotes_with_valuation 的基底列與條件 dict，輸出為
{"total": 總符合數, "results": 依 code 排序、上限 200 的結果列}。

衍生欄容錯：
- change_pct＝change/(close-change)*100（前收＝close-change）；前收為 0/None 或
  close/change 缺值時為 None。
- volume_lots＝volume/1000（張）；volume 為 None 時為 None。
條件比對時該欄為 None 的列一律不符合（僅在該條件有開時才排除）。
"""

RESULT_LIMIT = 200

# (條件鍵, 衍生/基底欄位, 比較函式)；門檻為 None（未指定）時該條件略過。
_CHECKS = (
    ("pe_min", "pe", lambda v, t: v >= t),
    ("pe_max", "pe", lambda v, t: v <= t),
    ("pb_min", "pb", lambda v, t: v >= t),
    ("pb_max", "pb", lambda v, t: v <= t),
    ("yield_min", "dividend_yield", lambda v, t: v >= t),
    ("change_pct_min", "change_pct", lambda v, t: v >= t),
    ("change_pct_max", "change_pct", lambda v, t: v <= t),
    ("volume_lots_min", "volume_lots", lambda v, t: v >= t),
)


def _change_pct(close: float | None, change: float | None) -> float | None:
    """漲跌幅％＝change/(close-change)*100；前收為 0/None 或缺值回 None。"""
    if close is None or change is None:
        return None
    prev_close = close - change
    if prev_close == 0:
        return None
    return round(change / prev_close * 100, 2)


def _enrich(row: dict) -> dict:
    """由基底列組出結果列（含衍生欄 change_pct、volume_lots）。"""
    volume = row.get("volume")
    return {
        "market": row.get("market"),
        "code": row.get("code"),
        "name": row.get("name"),
        "close": row.get("close"),
        "change_pct": _change_pct(row.get("close"), row.get("change")),
        "pe": row.get("pe"),
        "pb": row.get("pb"),
        "dividend_yield": row.get("dividend_yield"),
        "volume_lots": volume / 1000 if volume is not None else None,
    }


def _passes(row: dict, filters: dict) -> bool:
    """逐條件比對；該欄為 None 且該條件有開 → 不符合。"""
    for key, field, op in _CHECKS:
        threshold = filters.get(key)
        if threshold is None:
            continue
        value = row.get(field)
        if value is None or not op(value, threshold):
            return False
    return True


def screen(rows: list[dict], filters: dict) -> dict:
    """套用衍生欄與複合條件，回符合結果（依 code 排序、上限 200）與總符合數。"""
    matched = [r for r in (_enrich(row) for row in rows) if _passes(r, filters)]
    matched.sort(key=lambda r: r["code"] or "")
    return {"total": len(matched), "results": matched[:RESULT_LIMIT]}
