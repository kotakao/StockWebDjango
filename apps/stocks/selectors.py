"""stocks 唯讀查詢（spec §3.2、D13）：company_research / research_theme（純 default 庫）。

進 DB、出 dict，不含商業邏輯；不觸及 market 連線。
"""

from django.utils import timezone

from .models import CompanyResearch, ResearchTheme


def company_research(code: str) -> dict | None:
    """取某代號的公司質化研究資料；查無回 None（多數股尚未匯入屬正常）。

    imported_at 以本地時區（Asia/Taipei）ISO 字串輸出，供前端顯示匯入日。
    """
    row = CompanyResearch.objects.filter(pk=code).first()
    if row is None:
        return None
    return {
        "name": row.name,
        "sector_en": row.sector_en,
        "industry_en": row.industry_en,
        "business_summary": row.business_summary,
        "themes": list(row.themes),
        "source_repo": row.source_repo,
        "imported_at": timezone.localtime(row.imported_at).isoformat(),
    }


def theme_titles(keys: list[str]) -> dict[str, str]:
    """題材 slug → 顯示名對照（僅回存在於 research_theme 的 key）。"""
    if not keys:
        return {}
    return dict(ResearchTheme.objects.filter(key__in=keys).values_list("key", "title"))
