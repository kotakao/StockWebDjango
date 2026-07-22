"""import_company_research：自 My-TW-Coverage 本機 clone 匯入公司質化資料（D13）。

來源：GitHub Timeverse/My-TW-Coverage（MIT，保留出處於 source_repo 欄位）。
只取質化層（業務簡介、英文板塊/產業、題材歸屬）；財務/估值/市值/企業價值一律不匯入，
供應鏈不做結構化。全程僅讀本機檔案（禁止連網下載）、僅寫 default 庫
（完全不觸及 market 連線與 market.db）。

用法：
    python manage.py import_company_research --source <clone路徑> [--source-commit <hash>]
    未帶 --source 時改用 settings.RESEARCH_SOURCE_DIR；兩者皆缺或路徑不存在則報錯退出。

冪等：公司與題材皆 upsert；themes 陣列以集合合併去重，重跑不累積重複。
題材成員在 CompanyResearch 尚無列者：建立僅含 code 的最小列（保留題材歸屬，
待公司檔匯入時補齊其餘欄位）。
"""

import logging
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.stocks.models import CompanyResearch, ResearchTheme

logger = logging.getLogger(__name__)

# 公司檔名：NNNN_公司名.md（代號 4-6 碼開頭）
COMPANY_FILE_RE = re.compile(r"^(\d{4,6})_(.+)\.md$")
# H1：# NNNN - 公司名 或 # NNNN - [[公司名]]
COMPANY_H1_RE = re.compile(r"^#\s+(\d{4,6})\s*-\s*(.+?)\s*$", re.M)
# 業務簡介區塊：至下一個 ## 標題或檔尾
SUMMARY_SECTION_RE = re.compile(r"^##\s*業務簡介\s*$(.*?)(?=^##\s|\Z)", re.M | re.S)
# 欄位行（板塊/產業取值；市值/企業價值僅辨識以排除，不匯入）
SECTOR_RE = re.compile(r"^\*\*板塊[:：]\*\*\s*(.*)$")
INDUSTRY_RE = re.compile(r"^\*\*產業[:：]\*\*\s*(.*)$")
FIELD_LINE_RE = re.compile(r"^\*\*(板塊|產業|市值|企業價值)[:：]\*\*")
# [[wikilink]]：[[名稱]] → 名稱、[[目標|顯示]] → 顯示
WIKILINK_RE = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
# 題材檔 H1 與成員行（成員代號以此正則乾淨取出）
THEME_H1_RE = re.compile(r"^#\s+([^#].*?)\s*$", re.M)
THEME_MEMBER_RE = re.compile(r"^-\s+\*\*(\d{4,6})\s+", re.M)


def strip_wikilinks(text: str) -> str:
    """去除 [[ ]] 標記：[[名稱]] → 名稱、[[目標|顯示]] → 顯示。"""
    return WIKILINK_RE.sub(r"\1", text)


def normalize_theme_key(stem: str) -> str:
    """題材 slug：檔名去副檔名後小寫、空白/底線轉連字號（如 "AI-伺服器" → "ai-伺服器"）。"""
    key = stem.strip().lower()
    key = re.sub(r"[\s_]+", "-", key)
    return key[:64]


def parse_company_file(text: str, fallback_name: str) -> dict | None:
    """解析單一公司檔，回欄位 dict；結構異常（缺 H1 或缺業務簡介區塊）回 None。

    - name：H1 的公司名（去 [[ ]]；H1 缺名時退回檔名的公司名部分）。
    - sector_en / industry_en：業務簡介區塊內的 **板塊:** / **產業:** 欄位行。
    - business_summary：業務簡介區塊內非欄位行的敘述段落，去 [[ ]] 後的純文字。
    """
    h1 = COMPANY_H1_RE.search(text)
    if not h1:
        return None
    section = SUMMARY_SECTION_RE.search(text)
    if not section:
        return None

    name = strip_wikilinks(h1.group(2)).strip() or fallback_name

    sector = industry = ""
    summary_lines: list[str] = []
    for line in section.group(1).splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if m := SECTOR_RE.match(stripped):
            sector = m.group(1).strip()
        elif m := INDUSTRY_RE.match(stripped):
            industry = m.group(1).strip()
        elif FIELD_LINE_RE.match(stripped):
            continue  # 市值/企業價值：不匯入（本專案已有更權威的 market 資料）
        else:
            summary_lines.append(strip_wikilinks(stripped))

    return {
        "name": name[:64],
        "sector_en": sector[:64],
        "industry_en": industry[:64],
        "business_summary": "\n".join(summary_lines),
    }


def parse_theme_file(text: str) -> dict | None:
    """解析單一題材檔，回 {title, description, members}；缺 H1 回 None。

    - title：H1 文字。
    - description：H1 之後首段連續 `>` 引言行（去 `>` 前綴）。
    - members：全檔以 `^-\\s+\\*\\*(\\d{4,6})\\s+` 取出的成員代號（去重保序）。
    """
    h1 = THEME_H1_RE.search(text)
    if not h1:
        return None

    description_lines: list[str] = []
    after_h1 = text[h1.end():].splitlines()
    for line in after_h1:
        stripped = line.strip()
        if not stripped:
            if description_lines:
                break  # 引言段結束
            continue  # H1 與引言間的空行
        if stripped.startswith(">"):
            description_lines.append(stripped.lstrip(">").strip())
        else:
            break  # 首個非引言內容行：引言段結束（或無引言）

    members = list(dict.fromkeys(THEME_MEMBER_RE.findall(text)))
    return {
        "title": h1.group(1).strip()[:128],
        "description": "\n".join(description_lines),
        "members": members,
    }


class Command(BaseCommand):
    """匯入 My-TW-Coverage 質化資料至 default 庫（company_research / research_theme）。"""

    help = "自 My-TW-Coverage 本機 clone 匯入公司業務簡介與題材歸屬（D13，只寫 default 庫）"

    def add_arguments(self, parser):
        """--source：clone 根目錄（優先於 settings 值）；--source-commit：來源版本。"""
        parser.add_argument(
            "--source",
            default="",
            help="My-TW-Coverage 本機 clone 根目錄；未提供時改用 settings.RESEARCH_SOURCE_DIR",
        )
        parser.add_argument(
            "--source-commit",
            default="",
            help="來源 repo 的 commit hash（記錄於 source_commit 欄位）",
        )

    def handle(self, *args, **options):
        """讀取來源目錄 → 匯入公司檔與題材檔；來源缺失明確報錯，單檔異常容錯跳過。"""
        source = options["source"] or getattr(settings, "RESEARCH_SOURCE_DIR", "")
        if not source:
            raise CommandError(
                "未提供來源路徑：請以 --source 或 settings.RESEARCH_SOURCE_DIR "
                "指定 My-TW-Coverage 本機 clone 目錄（不對外連網下載）"
            )
        root = Path(source)
        if not root.is_dir():
            raise CommandError(f"來源路徑不存在或非目錄：{root}")

        source_commit = (options["source_commit"] or "")[:40]

        with transaction.atomic():
            imported, skipped = self._import_companies(root, source_commit)
            themes, theme_skipped, linked, minimal = self._import_themes(root)

        self.stdout.write(
            f"公司檔：匯入 {imported}、跳過 {skipped}；"
            f"題材檔：匯入 {themes}、跳過 {theme_skipped}；"
            f"題材成員連結 {linked}（新建最小列 {minimal}）"
        )

    def _import_companies(self, root: Path, source_commit: str) -> tuple[int, int]:
        """解析 Pilot_Reports/**/NNNN_*.md → upsert CompanyResearch；回 (匯入數, 跳過數)。"""
        reports_dir = root / "Pilot_Reports"
        if not reports_dir.is_dir():
            logger.warning("來源缺 Pilot_Reports/ 目錄，略過公司檔匯入：%s", reports_dir)
            return 0, 0

        imported = skipped = 0
        for path in sorted(reports_dir.rglob("*.md")):
            m = COMPANY_FILE_RE.match(path.name)
            if not m:
                continue  # 非公司檔（如目錄說明檔）
            code, fallback_name = m.group(1), m.group(2)
            try:
                parsed = parse_company_file(
                    path.read_text(encoding="utf-8"), fallback_name
                )
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("公司檔讀取失敗，跳過：%s（%s）", path.name, exc)
                skipped += 1
                continue
            if parsed is None:
                logger.warning("公司檔結構異常（缺 H1 或業務簡介），跳過：%s", path.name)
                skipped += 1
                continue

            CompanyResearch.objects.update_or_create(
                code=code, defaults={**parsed, "source_commit": source_commit}
            )
            imported += 1
        return imported, skipped

    def _import_themes(self, root: Path) -> tuple[int, int, int, int]:
        """解析 themes/*.md → upsert ResearchTheme 並將 slug 併入成員 themes 陣列（去重）。

        回 (題材匯入數, 題材跳過數, 成員連結數, 新建最小列數)。
        """
        themes_dir = root / "themes"
        if not themes_dir.is_dir():
            logger.warning("來源缺 themes/ 目錄，略過題材匯入：%s", themes_dir)
            return 0, 0, 0, 0

        imported = skipped = 0
        membership: dict[str, set[str]] = {}  # code → 題材 slug 集合
        for path in sorted(themes_dir.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            try:
                parsed = parse_theme_file(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("題材檔讀取失敗，跳過：%s（%s）", path.name, exc)
                skipped += 1
                continue
            if parsed is None:
                logger.warning("題材檔結構異常（缺 H1），跳過：%s", path.name)
                skipped += 1
                continue

            key = normalize_theme_key(path.stem)
            ResearchTheme.objects.update_or_create(
                key=key,
                defaults={"title": parsed["title"], "description": parsed["description"]},
            )
            imported += 1
            for code in parsed["members"]:
                membership.setdefault(code, set()).add(key)

        linked = minimal = 0
        for code, slugs in sorted(membership.items()):
            row, created = CompanyResearch.objects.get_or_create(code=code)
            if created:
                minimal += 1
            merged = sorted(set(row.themes) | slugs)
            if merged != row.themes:
                row.themes = merged
                row.save(update_fields=["themes", "imported_at"])
            linked += len(slugs)
        return imported, skipped, linked, minimal
