"""screener 頁面殼與條件選股 API（D8）。

- index：條件選股頁面殼（掛載 Vue app）。
- ScreenerResultsView：GET /api/screener/results，最新交易日行情＋估值複合篩選。

基底資料（quotes_with_valuation）整包以 Redis 快取；篩選本身每請求即時計算（不快取）。
純唯讀存取 market.db，依鐵律不做任何寫入。
"""

from django.core.cache import cache
from django.shortcuts import render
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market import selectors

from . import services

CACHE_TTL = 600  # 10 分鐘（spec §7）
CACHE_KEY = "screener:base:{date}"  # 前綴 swd:v1 由 CACHES 設定加上

# 支援的篩選條件（皆選填，數值）。
FILTER_KEYS = (
    "pe_min",
    "pe_max",
    "pb_min",
    "pb_max",
    "yield_min",
    "change_pct_min",
    "change_pct_max",
    "volume_lots_min",
)


def index(request):
    """條件選股頁面殼，繼承 base.html，內容由 Vue app 渲染。"""
    return render(request, "screener/index.html")


def _parse_filters(query_params) -> dict:
    """自 query 參數解析數值條件；非數值拋 ValidationError（→400）；至少需一個條件。"""
    filters = {}
    for key in FILTER_KEYS:
        raw = query_params.get(key)
        if raw is None or raw == "":
            continue
        try:
            filters[key] = float(raw)
        except (TypeError, ValueError):
            raise ValidationError(f"{key} 必須為數值") from None
    if not filters:
        raise ValidationError("至少需指定一個篩選條件")
    return filters


class ScreenerResultsView(APIView):
    """條件選股：最新交易日全體行情 LEFT JOIN 同日估值，套用複合條件篩選。

    基底資料整包 Redis 快取（key `screener:base:{date}`，前綴 swd:v1 由 CACHES 設定加上）；
    篩選每請求即時計算。daily_quotes 無任何資料時回 200 空結果。
    """

    def get(self, request):
        """回傳 {"date": 最新交易日, "total": 總符合數, "results": [...]}。"""
        filters = _parse_filters(request.query_params)

        latest = selectors.latest_trade_date()
        if latest is None:
            return Response({"date": None, "total": 0, "results": []})

        cache_key = CACHE_KEY.format(date=latest)
        base = cache.get(cache_key)
        if base is None:
            base = selectors.quotes_with_valuation(latest)
            cache.set(cache_key, base, timeout=CACHE_TTL)

        result = services.screen(base, filters)
        return Response({"date": latest, **result})
