"""stocks selectors 測試（D13）：company_research / theme_titles（純 default 庫）。"""

import pytest

from apps.stocks import selectors
from apps.stocks.models import CompanyResearch, ResearchTheme

pytestmark = pytest.mark.django_db


def test_company_research_none_when_absent():
    """查無代號 → None（多數股尚未匯入屬正常）。"""
    assert selectors.company_research("2330") is None


def test_company_research_returns_dict():
    """有資料 → 回含質化欄位的 dict；imported_at 為 ISO 字串。"""
    CompanyResearch.objects.create(
        code="2330",
        name="台積電",
        sector_en="Technology",
        industry_en="Semiconductors",
        business_summary="全球最大晶圓代工廠。",
        themes=["ai-伺服器"],
    )

    data = selectors.company_research("2330")

    assert data is not None
    assert data["name"] == "台積電"
    assert data["sector_en"] == "Technology"
    assert data["industry_en"] == "Semiconductors"
    assert data["business_summary"] == "全球最大晶圓代工廠。"
    assert data["themes"] == ["ai-伺服器"]
    assert data["source_repo"] == "Timeverse/My-TW-Coverage"
    assert isinstance(data["imported_at"], str) and data["imported_at"]


def test_theme_titles_maps_existing_keys_only():
    """theme_titles：僅回存在的 slug → title 對照；空輸入回空 dict。"""
    ResearchTheme.objects.create(key="ai-伺服器", title="AI 伺服器供應鏈")

    assert selectors.theme_titles(["ai-伺服器", "unknown"]) == {"ai-伺服器": "AI 伺服器供應鏈"}
    assert selectors.theme_titles([]) == {}
