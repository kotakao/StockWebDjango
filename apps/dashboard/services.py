"""dashboard 純商業邏輯（spec §3.2）：組裝儀表板四序列，不碰 HTTP、不查 DB。

輸入為 selectors 取出的 market_daily 列（dict，日期由舊到新）；
輸出為前端四張圖卡所需序列。缺欄容錯：
- 原始序列（指數、成交金額、漲跌家數、融資餘額）缺值以 None 帶出。
- 累積序列（三大法人買賣超、A/D Line）缺值視為當日 0，維持連續累積曲線。
"""

import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

SHARES_PER_LOT = 1000  # 股→張換算：1 張 = 1000 股
YI = 100_000_000  # 億：金額（元）→億元換算

# ---- 近期市場警示（D12）：StockDCBot reports JSON 讀取／正規化 ----
_REPORT_GLOB = "taiwan_stock_report_*.json"  # 檔名格式：..._YYYYMMDD.json
_LOOKBACK_DAYS = 14  # 自最新報告日回溯的日曆日上限（掃描邊界）


def _round(value: float | None, ndigits: int) -> float | None:
    """None 保持 None，否則四捨五入至指定小數位。"""
    return None if value is None else round(value, ndigits)


def _raw_series(rows: list[dict], field: str, transform: Callable[[float], float] | None = None):
    """原始序列：逐列取欄位，缺值（None）保留 None，可選數值轉換。"""
    out: list[float | None] = []
    for row in rows:
        value = row.get(field)
        if value is None:
            out.append(None)
        else:
            out.append(transform(value) if transform else value)
    return out


def _cumulative(rows: list[dict], value_of: Callable[[dict], float | None]) -> list[float]:
    """累積序列：逐列取值（None 視為 0），輸出當日的累積總和。"""
    out: list[float] = []
    running = 0.0
    for row in rows:
        value = value_of(row)
        if value is not None:
            running += value
        out.append(running)
    return out


def _lots(shares: float | None) -> float | None:
    """股→張（÷1000）；None 保持 None。"""
    return None if shares is None else shares / SHARES_PER_LOT


def build_dashboard_summary(rows: list[dict], days: int) -> dict:
    """將 market_daily 列組裝為儀表板四序列（回傳可 JSON 序列化的 dict）。

    rows：日期由舊到新的 market_daily dict 列表。
    四序列：
      1. institution：三大法人（外資/投信/自營商）買賣超「張」的累積和序列。
      2. breadth：漲跌家數與 A/D Line（每日 up-down 的累積）。
      3. index：指數收盤與成交金額（億元）。
      4. margin：融資餘額趨勢。
    """
    dates = [row.get("date") for row in rows]

    institution = {
        "foreign": [
            _round(v, 3) for v in _cumulative(rows, lambda r: _lots(r.get("foreign_net")))
        ],
        "trust": [
            _round(v, 3) for v in _cumulative(rows, lambda r: _lots(r.get("trust_net")))
        ],
        "dealer": [
            _round(v, 3) for v in _cumulative(rows, lambda r: _lots(r.get("dealer_net")))
        ],
    }

    def _up_minus_down(row: dict) -> float | None:
        up, down = row.get("up_count"), row.get("down_count")
        if up is None and down is None:
            return None
        return (up or 0) - (down or 0)

    breadth = {
        "up": _raw_series(rows, "up_count"),
        "down": _raw_series(rows, "down_count"),
        "ad_line": _cumulative(rows, _up_minus_down),
    }

    index = {
        "close": _raw_series(rows, "index_close"),
        "turnover_100m": _raw_series(rows, "turnover", lambda v: round(v / YI, 2)),
    }

    margin = {"balance": _raw_series(rows, "margin_balance")}

    return {
        "days": days,
        "count": len(rows),
        "dates": dates,
        "institution": institution,
        "breadth": breadth,
        "index": index,
        "margin": margin,
    }


def _report_date_from_name(path: Path) -> str | None:
    """由檔名末段 YYYYMMDD 取報告日（回 ISO "YYYY-MM-DD"）；無法解析回 None。"""
    token = path.stem.rsplit("_", 1)[-1]
    try:
        return datetime.strptime(token, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def _select_report_files(reports_dir: Path, days: int) -> list[Path]:
    """挑最近 days 個報告檔（依檔名日期新到舊，最多自最新報告回溯 14 個日曆日）。

    遞迴掃描（真實佈局為 reports/YYYY-MM/*.json）；檔名日期無法解析者略過。
    """
    dated: list[tuple[str, Path]] = []
    for path in reports_dir.glob(f"**/{_REPORT_GLOB}"):
        iso = _report_date_from_name(path)
        if iso is not None:
            dated.append((iso, path))
    if not dated:
        return []
    dated.sort(key=lambda item: item[0], reverse=True)  # 新→舊
    anchor = datetime.fromisoformat(dated[0][0]).date()
    cutoff = (anchor - timedelta(days=_LOOKBACK_DAYS)).isoformat()
    within = [path for iso, path in dated if iso >= cutoff]
    return within[:days]


def _normalize_alerts(payload: dict, fallback_date: str | None) -> list[dict]:
    """將單一報告的 sections.market_alerts 正規化為前端所需列。

    每筆 → {date, rule, direction, message}：date 取報告頂層 date（缺則用檔名日）；
    rule/direction/message 取中文鍵「規則」「方向」「訊息」，缺任一鍵以 None 容錯
    （不跳過整筆）。舊格式（無 market_alerts 鍵）或結構異常則拋 ValueError（呼叫端跳過整檔）。
    """
    if not isinstance(payload, dict):
        raise ValueError("報告頂層非 JSON 物件")
    sections = payload.get("sections")
    if not isinstance(sections, dict) or "market_alerts" not in sections:
        raise ValueError("舊格式報告（無 sections.market_alerts 鍵）")
    report_date = payload.get("date") or fallback_date
    raw = sections.get("market_alerts") or []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue  # 非 dict 的警示項略過
        out.append(
            {
                "date": report_date,
                "rule": item.get("規則"),
                "direction": item.get("方向"),
                "message": item.get("訊息"),
            }
        )
    return out


def collect_recent_alerts(reports_dir: str | None, days: int) -> tuple[list[dict], str | None]:
    """讀最近 days 個交易日報告，彙整市場警示。

    回傳 (alerts, reason)：
      - reports_dir 未設定／目錄不存在／無任何可讀報告 → ([], 原因字串)。
      - 有可讀報告（含 market_alerts 鍵，即使為空）但皆無警示 → ([], None)。
      - 有警示 → (警示列表（新→舊），None)。
    缺檔／壞 JSON／舊格式逐檔容錯跳過並記 log，不使整包失敗。
    """
    if not reports_dir:
        return [], "未設定 REPORTS_DIR，無法讀取市場警示報告。"
    base = Path(reports_dir)
    if not base.is_dir():
        return [], "報告目錄不存在，無法讀取市場警示。"

    files = _select_report_files(base, days)
    if not files:
        return [], "查無可讀取的報告檔。"

    alerts: list[dict] = []
    readable = 0
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            file_alerts = _normalize_alerts(payload, _report_date_from_name(path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("略過無法解析的報告檔 %s：%s", path.name, exc)
            continue
        readable += 1
        alerts.extend(file_alerts)

    if readable == 0:
        return [], "查無可讀取的報告檔。"
    return alerts, None
