"""GET /api/dashboard/alerts API 測試（D12）：days 邊界驗證、reason 分支、快取。

純檔案讀取，不觸及 market 資料庫；以 settings.REPORTS_DIR 指向 tmp_path 造假報告。
"""

import json

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

client = APIClient()


@pytest.fixture(autouse=True)
def _clear_cache():
    """每測試前後清快取，避免快取／節流狀態跨測試污染。"""
    cache.clear()
    yield
    cache.clear()


def _write_report(base, yyyymmdd: str, alerts):
    iso = f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    month_dir = base / iso[:7]
    month_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "date": iso,
        "generated_at": f"{iso}T16:23:35+08:00",
        "sections": {"market_alerts": alerts},
    }
    (month_dir / f"taiwan_stock_report_{yyyymmdd}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


_ALERT = {
    "規則": "成交量能異常",
    "方向": "爆量",
    "倍數": 2.13,
    "訊息": "成交金額 8,681 億元為近 20 日均值 2.13 倍（爆量）",
}


def test_invalid_days_non_integer_400():
    """days 非整數 → 400 {"error": ...}。"""
    resp = client.get("/api/dashboard/alerts?days=abc")
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.parametrize("bad", ["0", "11", "-1"])
def test_days_out_of_range_400(bad):
    """days 超出 1~10 → 400 {"error": ...}。"""
    resp = client.get(f"/api/dashboard/alerts?days={bad}")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_reports_dir_unset_returns_reason(settings):
    """未設 REPORTS_DIR → 200，alerts []、reason 有值。"""
    settings.REPORTS_DIR = ""
    resp = client.get("/api/dashboard/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["alerts"] == []
    assert data["reason"]


def test_reports_present_no_alerts_reason_none(settings, tmp_path):
    """有可讀報告但皆無警示 → alerts []、reason 為 None（非錯誤）。"""
    _write_report(tmp_path, "20260716", [])
    settings.REPORTS_DIR = str(tmp_path)
    resp = client.get("/api/dashboard/alerts?days=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["alerts"] == []
    assert data["reason"] is None


def test_reports_with_alerts_returns_normalized(settings, tmp_path):
    """有警示 → 200，回正規化 {date, rule, direction, message}。"""
    _write_report(tmp_path, "20260716", [_ALERT])
    settings.REPORTS_DIR = str(tmp_path)
    resp = client.get("/api/dashboard/alerts?days=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reason"] is None
    assert data["alerts"] == [
        {
            "date": "2026-07-16",
            "rule": "成交量能異常",
            "direction": "爆量",
            "message": "成交金額 8,681 億元為近 20 日均值 2.13 倍（爆量）",
        }
    ]


def test_default_days_ok(settings, tmp_path):
    """未帶 days → 預設 5，200。"""
    _write_report(tmp_path, "20260716", [_ALERT])
    settings.REPORTS_DIR = str(tmp_path)
    resp = client.get("/api/dashboard/alerts")
    assert resp.status_code == 200
    assert len(resp.json()["alerts"]) == 1


def test_cache_key_populated(settings, tmp_path):
    """整包以 key alerts:{days} 快取（前綴 swd:v1 由 CACHES 設定加上）。"""
    _write_report(tmp_path, "20260716", [_ALERT])
    settings.REPORTS_DIR = str(tmp_path)
    client.get("/api/dashboard/alerts?days=5")
    cached = cache.get("alerts:5")
    assert cached is not None
    assert cached["alerts"][0]["rule"] == "成交量能異常"
