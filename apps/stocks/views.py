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

from .models import StockSnapshot
from .serializers import StockSnapshotSerializer
from .tasks import refresh_snapshot

CODE_RE = re.compile(r"^[A-Za-z0-9]{4,6}$")  # 代號：4-6 位英數
CACHE_TTL = 600  # 10 分鐘（spec §7）
CACHE_KEY = "stock:{code}"  # 前綴 swd:v1 由 CACHES 設定加上
RECENT_LIMIT = 20  # 近 N 個交易日快照


def query(request):
    """個股查詢頁面殼，繼承 base.html，內容區為佔位表單。"""
    return render(request, "stocks/query.html")


def _validate_code(code: str) -> str:
    """驗證代號 4-6 位英數；不合法拋 DRF ValidationError（→400）。"""
    if not CODE_RE.match(code or ""):
        raise ValidationError("code 需為 4-6 位英數")
    return code


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
