"""watchlist 頁面殼與自選股 API（D5）。

- index：自選股頁面殼（掛載 Vue app）。
- WatchlistSummaryView：GET /api/watchlist/summary，唯讀彙整＋Redis 快取。

user_id 取自 settings.WATCHLIST_USER_ID（對應 market.db watchlist/holdings 的 user_id）。
本功能純唯讀呈現，不提供任何編輯入口（編輯在 Discord /watch 與 Blazor 版）。
"""

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import build_watchlist_summary

CACHE_TTL = 600  # 10 分鐘（spec §7）
CACHE_KEY = "watchlist:{user_id}"  # 前綴 swd:v1 由 CACHES 設定加上


def index(request):
    """自選股頁面殼，繼承 base.html，內容由 Vue app 渲染。"""
    return render(request, "watchlist/index.html")


class WatchlistSummaryView(APIView):
    """自選股行情/估值與持股損益彙整（整包 Redis 快取，key watchlist:{user_id}）。"""

    def get(self, request):
        """回傳設定 user_id 的自選股與持股清單；兩者皆空回空清單（200）。"""
        user_id = settings.WATCHLIST_USER_ID
        cache_key = CACHE_KEY.format(user_id=user_id)

        payload = cache.get(cache_key)
        if payload is None:
            payload = build_watchlist_summary(user_id)
            cache.set(cache_key, payload, timeout=CACHE_TTL)

        return Response(payload)
