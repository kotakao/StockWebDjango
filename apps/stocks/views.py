"""stocks 頁面殼（D1）與個股快照 API（D3）。

- query：個股查詢頁面殼（D4 實作查詢 UI）。
- StockSummaryView：GET /api/stocks/{code}/summary，快照就緒回 200、否則 enqueue 並回 202。
"""

import re

from django.core.cache import cache
from django.shortcuts import render
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market import selectors

from . import selectors as stocks_selectors
from . import services
from .models import StockSnapshot
from .serializers import StockSnapshotSerializer
from .tasks import refresh_snapshot

CODE_RE = re.compile(r"^[A-Za-z0-9]{4,6}$")  # 代號：4-6 位英數
CACHE_TTL = 600  # 10 分鐘（spec §7）
CACHE_KEY = "stock:{code}"  # 前綴 swd:v1 由 CACHES 設定加上
REVENUE_CACHE_KEY = "stock:revenue:{code}"  # 月營收對比整包快取（前綴同上）
QUOTES_CACHE_KEY = "quotes:{code}:{days}:{adjusted}"  # 日 K 序列快取（前綴同上）
PEERS_CACHE_KEY = "peers:{code}"  # 同業對比整包快取（前綴同上）
RESEARCH_CACHE_KEY = "research:{code}"  # 公司質化研究整包快取（前綴同上）
RECENT_LIMIT = 20  # 近 N 個交易日快照
DEFAULT_DAYS = 252  # 日 K 預設近 252 交易日
MAX_DAYS = 252  # days 上限


def query(request):
    """個股查詢頁面殼，繼承 base.html，內容區為佔位表單。"""
    return render(request, "stocks/query.html")


def _validate_code(code: str) -> str:
    """驗證代號 4-6 位英數；不合法拋 DRF ValidationError（→400）。"""
    if not CODE_RE.match(code or ""):
        raise ValidationError("code 需為 4-6 位英數")
    return code


def _validate_days(raw: str | None) -> int:
    """驗證 days：1~252 整數，缺省回 252；非整數或超界拋 ValidationError（→400）。"""
    if raw in (None, ""):
        return DEFAULT_DAYS
    try:
        days = int(raw)
    except (TypeError, ValueError):
        raise ValidationError("days 需為 1~252 的整數") from None
    if not 1 <= days <= MAX_DAYS:
        raise ValidationError(f"days 需為 1~{MAX_DAYS}")
    return days


def _parse_adjusted(raw: str | None) -> bool:
    """解析 adjusted 布林參數，預設 True；僅 false/0/no（不分大小寫）視為未還原。"""
    if raw is None:
        return True
    return raw.strip().lower() not in ("false", "0", "no")


class StockSummaryView(APIView):
    """個股近期快照：最新指標卡＋近 20 個交易日列表（新到舊）。

    - 快照存在且 trade_date == market 庫 daily_quotes 最新交易日 → 200 回應（Redis 快取）。
    - 否則 enqueue refresh_snapshot 並回 202 {"status": "processing"}。
    - 查無代號（daily_quotes 無列）→ 400。
    """

    def get(self, request, code):
        """依快照就緒狀態回 200／202；代號格式錯或查無代號回 400。"""
        code = _validate_code(code)
        cache_key = CACHE_KEY.format(code=code)

        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        latest_day = selectors.latest_trade_date()
        snapshot = (
            StockSnapshot.objects.filter(code=code).order_by("-trade_date").first()
        )
        if snapshot and latest_day and str(snapshot.trade_date) == latest_day:
            recent = list(
                StockSnapshot.objects.filter(code=code).order_by("-trade_date")[
                    :RECENT_LIMIT
                ]
            )
            payload = {
                "code": code,
                "latest": StockSnapshotSerializer(snapshot).data,
                "recent": StockSnapshotSerializer(recent, many=True).data,
            }
            cache.set(cache_key, payload, timeout=CACHE_TTL)
            return Response(payload)

        # 快照缺漏或非最新：先確認代號存在，否則 400；存在則排程重算並回 202
        if not selectors.code_exists(code):
            raise ValidationError("查無此代號")

        refresh_snapshot.delay(code)
        return Response({"status": "processing"}, status=202)


class StockRevenueView(APIView):
    """個股月營收對比：monthly_revenue 全部月份列（新到舊）。

    - code 格式錯（非 4-6 位英數）→ 400 {"error": ...}。
    - 查無資料 → 200 空清單（代號存在與否由 summary API 把關，本端點單純反映現況）。
    - 整包 Redis 快取（key stock:revenue:{code}，前綴 swd:v1 由 CACHES 加上，TTL 10 分）。
    """

    def get(self, request, code):
        """回 {"code": ..., "months": [...]}，月份新到舊。"""
        code = _validate_code(code)
        cache_key = REVENUE_CACHE_KEY.format(code=code)

        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        payload = {"code": code, "months": selectors.monthly_revenue_rows(code)}
        cache.set(cache_key, payload, timeout=CACHE_TTL)
        return Response(payload)


class StockQuotesView(APIView):
    """個股日 K 序列：GET /api/stocks/{code}/quotes?days=252&adjusted=true。

    - code 非 4-6 位英數 → 400；days 非 1~252 整數 → 400。
    - 查無代號（daily_quotes 無列）→ 400。
    - 回傳日期舊到新的 OHLCV ＋ 三大法人淨額（張）序列（Redis 快取，TTL 10 分）。
    - adjusted 預設 true（前復權）；快取 key 含 days 與 adjusted 以區分。
    """

    def get(self, request, code):
        """回 {"code","days","adjusted","quotes":[...]}；quotes 日期舊到新。"""
        code = _validate_code(code)
        days = _validate_days(request.query_params.get("days"))
        adjusted = _parse_adjusted(request.query_params.get("adjusted"))

        cache_key = QUOTES_CACHE_KEY.format(
            code=code, days=days, adjusted=str(adjusted).lower()
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        if not selectors.code_exists(code):
            raise ValidationError("查無此代號")

        payload = {
            "code": code,
            "days": days,
            "adjusted": adjusted,
            "quotes": services.build_quotes(code, days, adjusted),
        }
        cache.set(cache_key, payload, timeout=CACHE_TTL)
        return Response(payload)


class StockPeersView(APIView):
    """同業比較：company_profile 同產業個股的最新估值/營收 YoY/毛利率對比。

    - code 非 4-6 位英數 → 400 {"error": ...}。
    - 查無代號（daily_quotes 無列）→ 400。
    - company_profile 缺表或該股無產業資料 → 200 {"peers": [], "reason": ...}。
    - 整包 Redis 快取（key peers:{code}，前綴 swd:v1 由 CACHES 加上，TTL 10 分）。
    """

    def get(self, request, code):
        """回 {"code", "peers": [...], "reason": ...}；本股列標 is_self。"""
        code = _validate_code(code)
        cache_key = PEERS_CACHE_KEY.format(code=code)

        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        if not selectors.code_exists(code):
            raise ValidationError("查無此代號")

        payload = {"code": code, **services.build_peers(code)}
        cache.set(cache_key, payload, timeout=CACHE_TTL)
        return Response(payload)


class StockResearchView(APIView):
    """公司質化研究（D13）：My-TW-Coverage 匯入的業務簡介與題材（純 default 庫）。

    - code 非 4-6 位英數 → 400 {"error": ...}。
    - 查無資料 → 200 {"code": code, "research": null}（多數股尚未匯入屬正常，非 404）。
    - 有資料 → research 含 name/sector_en/industry_en/business_summary/
      themes（[{key,title}]）/source_repo/imported_at。
    - 整包 Redis 快取（key research:{code}，前綴 swd:v1 由 CACHES 加上，TTL 10 分）。
    """

    def get(self, request, code):
        """回 {"code", "research": {...} | null}；題材列 {key,title}（缺定義退回 key）。"""
        code = _validate_code(code)
        cache_key = RESEARCH_CACHE_KEY.format(code=code)

        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        research = stocks_selectors.company_research(code)
        if research is not None:
            titles = stocks_selectors.theme_titles(research["themes"])
            research["themes"] = [
                {"key": key, "title": titles.get(key, key)} for key in research["themes"]
            ]

        payload = {"code": code, "research": research}
        cache.set(cache_key, payload, timeout=CACHE_TTL)
        return Response(payload)
