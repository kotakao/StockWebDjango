"""近期市場警示 services 單元測試（D12，純檔案讀取，不進 DB）。

以 tmp_path 造假報告檔，涵蓋：中文鍵真實形狀的非空警示、空陣列、無 market_alerts
鍵的舊格式、壞 JSON、缺檔/缺目錄、缺共同鍵以 None 容錯、14 日回溯上限、days 上限。
報告真實佈局為 reports/YYYY-MM/taiwan_stock_report_YYYYMMDD.json。
"""

import json

from apps.dashboard.services import _normalize_alerts, collect_recent_alerts


def _write_report(base, yyyymmdd: str, *, alerts=None, top_date="__auto__", omit_alerts=False):
    """在 base/YYYY-MM/ 下寫一份報告 JSON（比照 StockDCBot 真實佈局與頂層結構）。"""
    iso = f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    month_dir = base / iso[:7]
    month_dir.mkdir(parents=True, exist_ok=True)
    sections = {"market_summary": {}, "overview": {}}
    if not omit_alerts:
        sections["market_alerts"] = alerts if alerts is not None else []
    payload = {
        "date": iso if top_date == "__auto__" else top_date,
        "generated_at": f"{iso}T16:23:35+08:00",
        "firm_level": "standard",
        "api_status": {"ok": 1, "total": 1},
        "sections": sections,
    }
    path = month_dir / f"taiwan_stock_report_{yyyymmdd}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


# 依派工提供的四規則真實中文鍵形狀
_VOLUME_ALERT = {
    "規則": "成交量能異常",
    "方向": "爆量",
    "倍數": 2.13,
    "訊息": "成交金額 8,681 億元為近 20 日均值 2.13 倍（爆量）",
}
_FOREIGN_ALERT = {
    "規則": "外資買賣超異常",
    "方向": "賣超",
    "偏離標準差": 3.2,
    "訊息": "外資賣超偏離近 60 日均值 3.2 個標準差（門檻 2σ）",
}


def test_non_empty_alerts_normalized_fields(tmp_path):
    """非空警示：正規化為 {date, rule, direction, message}，date 取報告頂層 date。"""
    _write_report(tmp_path, "20260716", alerts=[_VOLUME_ALERT, _FOREIGN_ALERT])
    alerts, reason = collect_recent_alerts(str(tmp_path), 5)
    assert reason is None
    assert alerts == [
        {
            "date": "2026-07-16",
            "rule": "成交量能異常",
            "direction": "爆量",
            "message": "成交金額 8,681 億元為近 20 日均值 2.13 倍（爆量）",
        },
        {
            "date": "2026-07-16",
            "rule": "外資買賣超異常",
            "direction": "賣超",
            "message": "外資賣超偏離近 60 日均值 3.2 個標準差（門檻 2σ）",
        },
    ]


def test_missing_common_key_is_none_not_skipped(tmp_path):
    """警示缺某一共同鍵（此處缺「方向」）→ 該欄 None，整筆不跳過。"""
    partial = {"規則": "融資餘額異常", "增減幅(%)": 5.1, "訊息": "融資餘額單日增加 5.1%（門檻 3%）"}
    out = _normalize_alerts(
        {"date": "2026-07-16", "sections": {"market_alerts": [partial]}}, "2026-07-16"
    )
    assert out == [
        {
            "date": "2026-07-16",
            "rule": "融資餘額異常",
            "direction": None,
            "message": "融資餘額單日增加 5.1%（門檻 3%）",
        }
    ]


def test_empty_alerts_reason_none(tmp_path):
    """報告存在但 market_alerts 為空 → alerts []、reason None（非錯誤）。"""
    _write_report(tmp_path, "20260716", alerts=[])
    alerts, reason = collect_recent_alerts(str(tmp_path), 5)
    assert alerts == []
    assert reason is None


def test_old_format_no_market_alerts_key_skipped(tmp_path):
    """舊格式（無 market_alerts 鍵）唯一檔 → 視為不可讀，reason 有值、alerts []。"""
    _write_report(tmp_path, "20260716", omit_alerts=True)
    alerts, reason = collect_recent_alerts(str(tmp_path), 5)
    assert alerts == []
    assert reason == "查無可讀取的報告檔。"


def test_bad_json_skipped_but_others_survive(tmp_path):
    """壞 JSON 檔逐檔跳過，不使整包失敗；同批其他好檔仍正常回。"""
    _write_report(tmp_path, "20260716", alerts=[_VOLUME_ALERT])
    bad = tmp_path / "2026-07" / "taiwan_stock_report_20260715.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    alerts, reason = collect_recent_alerts(str(tmp_path), 5)
    assert reason is None
    assert [a["rule"] for a in alerts] == ["成交量能異常"]


def test_reports_dir_not_set_returns_reason(tmp_path):
    """REPORTS_DIR 未設定（空字串/None）→ alerts []、reason 有值。"""
    for value in ("", None):
        alerts, reason = collect_recent_alerts(value, 5)
        assert alerts == []
        assert reason


def test_reports_dir_missing_returns_reason(tmp_path):
    """目錄不存在 → alerts []、reason 有值。"""
    alerts, reason = collect_recent_alerts(str(tmp_path / "nope"), 5)
    assert alerts == []
    assert reason


def test_empty_dir_returns_reason(tmp_path):
    """目錄存在但無任何報告檔 → alerts []、reason 有值。"""
    alerts, reason = collect_recent_alerts(str(tmp_path), 5)
    assert alerts == []
    assert reason


def test_lookback_14_days_cap(tmp_path):
    """自最新報告日回溯上限 14 個日曆日：超過者不納入（即使 days 未滿）。"""
    _write_report(tmp_path, "20260716", alerts=[dict(_VOLUME_ALERT, 訊息="新")])  # 最新（錨點）
    _write_report(tmp_path, "20260701", alerts=[dict(_VOLUME_ALERT, 訊息="邊界內")])  # 15 日前→界外
    _write_report(tmp_path, "20260703", alerts=[dict(_VOLUME_ALERT, 訊息="界內")])  # 13 日前→界內
    alerts, reason = collect_recent_alerts(str(tmp_path), 10)
    msgs = [a["message"] for a in alerts]
    assert "新" in msgs
    assert "界內" in msgs
    assert "邊界內" not in msgs  # 07-01 距 07-16 為 15 日，超過 14 日上限


def test_days_limits_number_of_reports(tmp_path):
    """days 限制取用的報告檔數（新→舊取前 N，每檔警示標各自日期）。"""
    _write_report(tmp_path, "20260716", alerts=[dict(_VOLUME_ALERT, 訊息="d16")])
    _write_report(tmp_path, "20260715", alerts=[dict(_VOLUME_ALERT, 訊息="d15")])
    _write_report(tmp_path, "20260714", alerts=[dict(_VOLUME_ALERT, 訊息="d14")])
    alerts, _ = collect_recent_alerts(str(tmp_path), 2)
    dates = {a["date"] for a in alerts}
    assert dates == {"2026-07-16", "2026-07-15"}  # 僅最新 2 個交易日


def test_date_fallback_from_filename(tmp_path):
    """報告頂層無 date 時，警示 date 以檔名 YYYYMMDD 回填。"""
    _write_report(tmp_path, "20260716", alerts=[_VOLUME_ALERT], top_date=None)
    alerts, _ = collect_recent_alerts(str(tmp_path), 5)
    assert alerts[0]["date"] == "2026-07-16"
