"""import_company_research 匯入指令測試（D13）。

於 tmp_path 造假的 Pilot_Reports/ 與 themes/ 小樣本 fixture，全程不連網、
不碰 market 連線（僅寫 default 測試庫）。涵蓋：業務簡介欄位與敘述去 [[ ]]、
H1 帶/不帶方括號、題材成員代號抽取與 themes 併入去重、結構異常單檔跳過、
缺 --source 報錯、冪等重跑。
"""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.stocks.models import CompanyResearch, ResearchTheme

pytestmark = pytest.mark.django_db

COMPANY_2330 = """# 2330 - 台積電

## 業務簡介

**板塊:** Technology
**產業:** Semiconductors
**市值:** 20.5 兆 TWD
**企業價值:** 20.1 兆 TWD

台積電為全球最大晶圓代工廠，客戶包括 [[Apple]] 與 [[輝達|NVIDIA]]，居 [[半導體]] 產業領導地位。

## 供應鏈位置

上游：[[設備商]]

## 主要客戶及供應商

- [[Apple]]

## 財務概況

| 年度 | 營收 |
|---|---|
| 2025 | 999 |
"""

COMPANY_2317_BRACKET_H1 = """# 2317 - [[鴻海]]

## 業務簡介

**板塊:** Technology
**產業:** Electronic Components

鴻海為全球最大電子代工廠。
"""

COMPANY_BROKEN = """# 9998 - 壞檔公司

## 供應鏈位置

（缺業務簡介區塊，應容錯跳過）
"""

THEME_AI = """# AI 伺服器供應鏈

> 涵蓋 AI 伺服器上中下游的台股供應鏈。

## 上游

- **2330 台積電** (Semiconductors)

## 中游

- **2317 鴻海** (Electronic Components)

## 下游

- **9910 僅題材公司** (Unknown)
"""

THEME_README = """# themes 目錄說明

本目錄為題材檔清單（應被略過，不匯入為題材）。
"""


def _write_source(tmp_path, companies=None, themes=None):
    """建立假的 My-TW-Coverage clone 目錄結構。"""
    reports = tmp_path / "Pilot_Reports" / "batch1"
    reports.mkdir(parents=True)
    for filename, text in (companies or {}).items():
        (reports / filename).write_text(text, encoding="utf-8")
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()
    for filename, text in (themes or {}).items():
        (themes_dir / filename).write_text(text, encoding="utf-8")
    return tmp_path


def test_missing_source_raises():
    """未帶 --source 且 settings.RESEARCH_SOURCE_DIR 未設定 → 明確報錯，不靜默。"""
    with pytest.raises(CommandError, match="來源路徑"):
        call_command("import_company_research")


def test_nonexistent_source_raises(tmp_path):
    """--source 指向不存在路徑 → 明確報錯退出。"""
    with pytest.raises(CommandError, match="不存在"):
        call_command("import_company_research", source=str(tmp_path / "nope"))


def test_company_fields_parsed_and_wikilinks_stripped(tmp_path):
    """業務簡介欄位（板塊/產業）入庫、敘述去 [[ ]]；市值/企業價值不匯入任何欄位。"""
    src = _write_source(tmp_path, companies={"2330_台積電.md": COMPANY_2330})

    call_command("import_company_research", source=str(src), source_commit="a" * 40)

    row = CompanyResearch.objects.get(code="2330")
    assert row.name == "台積電"
    assert row.sector_en == "Technology"
    assert row.industry_en == "Semiconductors"
    assert "[[" not in row.business_summary and "]]" not in row.business_summary
    assert "Apple" in row.business_summary
    assert "NVIDIA" in row.business_summary  # [[目標|顯示]] 取顯示名
    assert "半導體" in row.business_summary
    assert "市值" not in row.business_summary  # 欄位行不混入敘述
    assert row.source_repo == "Timeverse/My-TW-Coverage"
    assert row.source_commit == "a" * 40


def test_h1_with_brackets_parsed(tmp_path):
    """H1 公司名帶 [[ ]] 方括號 → 去除後入庫。"""
    src = _write_source(tmp_path, companies={"2317_鴻海.md": COMPANY_2317_BRACKET_H1})

    call_command("import_company_research", source=str(src))

    row = CompanyResearch.objects.get(code="2317")
    assert row.name == "鴻海"
    assert row.industry_en == "Electronic Components"


def test_broken_company_file_skipped_without_failing_batch(tmp_path):
    """結構異常單檔（缺業務簡介）容錯跳過，其餘檔案照常匯入。"""
    src = _write_source(
        tmp_path,
        companies={
            "2330_台積電.md": COMPANY_2330,
            "9998_壞檔公司.md": COMPANY_BROKEN,
        },
    )

    call_command("import_company_research", source=str(src))

    assert CompanyResearch.objects.filter(code="2330").exists()
    assert not CompanyResearch.objects.filter(code="9998").exists()


def test_theme_parsed_and_members_merged(tmp_path):
    """題材檔：key 正規化、title 取 H1、description 取引言、成員 slug 併入 themes；
    README.md 略過；無公司檔的成員建立僅含 code 的最小列。"""
    src = _write_source(
        tmp_path,
        companies={"2330_台積電.md": COMPANY_2330},
        themes={"AI-伺服器.md": THEME_AI, "README.md": THEME_README},
    )

    call_command("import_company_research", source=str(src))

    theme = ResearchTheme.objects.get(key="ai-伺服器")
    assert theme.title == "AI 伺服器供應鏈"
    assert theme.description == "涵蓋 AI 伺服器上中下游的台股供應鏈。"
    assert ResearchTheme.objects.count() == 1  # README.md 不匯入

    assert CompanyResearch.objects.get(code="2330").themes == ["ai-伺服器"]
    # 題材列出但無公司檔者：建立僅含 code 的最小列（保留題材歸屬）
    minimal = CompanyResearch.objects.get(code="9910")
    assert minimal.themes == ["ai-伺服器"]
    assert minimal.name == "" and minimal.business_summary == ""
    # 2317 無公司檔也在題材中 → 亦為最小列
    assert CompanyResearch.objects.get(code="2317").themes == ["ai-伺服器"]


def test_idempotent_rerun_no_duplicates(tmp_path):
    """冪等：重跑不重複——列數不變、themes 陣列不累積重複。"""
    src = _write_source(
        tmp_path,
        companies={"2330_台積電.md": COMPANY_2330},
        themes={"AI-伺服器.md": THEME_AI},
    )

    call_command("import_company_research", source=str(src))
    call_command("import_company_research", source=str(src))

    assert CompanyResearch.objects.count() == 3  # 2330 + 最小列 2317/9910
    assert ResearchTheme.objects.count() == 1
    assert CompanyResearch.objects.get(code="2330").themes == ["ai-伺服器"]
    assert CompanyResearch.objects.get(code="9910").themes == ["ai-伺服器"]
