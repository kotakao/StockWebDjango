"""GET /api/stocks/{code}/research API 測試（D13）：code 格式 400、查無資料
research=null（200 非 404）、有資料 200、快取。純 default 庫，不碰 market 連線。
"""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.stocks import selectors
from apps.stocks.models import CompanyResearch, ResearchTheme

client = APIClient()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.parametrize("bad", ["12", "1234567", "abc$"])
def test_research_400_when_code_format_invalid(bad):
    """代號格式非 4-6 位英數 → 400 {"error": ...}。"""
    resp = client.get(f"/api/stocks/{bad}/research")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_research_200_null_when_absent():
    """查無資料 → 200 research=null（多數股尚未匯入屬正常，非 404）。"""
    resp = client.get("/api/stocks/2330/research")

    assert resp.status_code == 200
    assert resp.json() == {"code": "2330", "research": None}


def test_research_200_with_data():
    """有資料 → 200，themes 為 [{key,title}]（缺題材定義時 title 退回 key）。"""
    CompanyResearch.objects.create(
        code="2330",
        name="台積電",
        sector_en="Technology",
        industry_en="Semiconductors",
        business_summary="全球最大晶圓代工廠。",
        themes=["ai-伺服器", "no-def"],
    )
    ResearchTheme.objects.create(key="ai-伺服器", title="AI 伺服器供應鏈")

    resp = client.get("/api/stocks/2330/research")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "2330"
    research = body["research"]
    assert research["name"] == "台積電"
    assert research["sector_en"] == "Technology"
    assert research["industry_en"] == "Semiconductors"
    assert research["business_summary"] == "全球最大晶圓代工廠。"
    assert research["themes"] == [
        {"key": "ai-伺服器", "title": "AI 伺服器供應鏈"},
        {"key": "no-def", "title": "no-def"},
    ]
    assert research["source_repo"] == "Timeverse/My-TW-Coverage"
    assert research["imported_at"]


def test_research_cache_second_call_does_not_requery(monkeypatch):
    """整包快取：第二次請求命中 research:{code}，不再查 default 庫。"""
    CompanyResearch.objects.create(code="2330", name="台積電")

    calls = {"n": 0}
    real = selectors.company_research

    def _counting(code):
        calls["n"] += 1
        return real(code)

    monkeypatch.setattr("apps.stocks.views.stocks_selectors.company_research", _counting)

    first = client.get("/api/stocks/2330/research")
    second = client.get("/api/stocks/2330/research")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["n"] == 1
    assert cache.get("research:2330") is not None
