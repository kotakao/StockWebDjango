"""conferences 頁面殼與法說會 API（D6）。

- index：法說會頁面殼（掛載 Vue app）。
- ConferenceSummaryView：GET /api/conferences/summary?days=30，唯讀彙整＋Redis 快取。

純唯讀呈現 market.db 的 investor_conferences（DC-K 入庫）；不提供任何編輯。
無商業邏輯（僅兩次唯讀查詢＋組裝信封），故不設 services 層。
"""

from django.core.cache import cache
from django.shortcuts import render
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market import selectors

DAYS_DEFAULT = 30
DAYS_MIN = 1
DAYS_MAX = 90
RECENT_LIMIT = 20
CACHE_TTL = 600  # 10 分鐘（spec §7）


def index(request):
    """法說會頁面殼，繼承 base.html，內容由 Vue app 渲染。"""
    return render(request, "conferences/index.html")


def _parse_days(raw: str | None) -> int:
    """驗證 days 參數：1~90 整數，預設 30；不合法拋 DRF ValidationError（→400）。"""
    if raw is None or raw == "":
        return DAYS_DEFAULT
    try:
        days = int(raw)
    except (TypeError, ValueError):
        raise ValidationError("days 必須為整數") from None
    if not (DAYS_MIN <= days <= DAYS_MAX):
        raise ValidationError(f"days 需介於 {DAYS_MIN} 與 {DAYS_MAX}")
    return days


class ConferenceSummaryView(APIView):
    """法說會彙整：即將召開（依 days 窗）＋近期公告（固定近 20 筆）。

    整包回應以 Redis 快取（key `conferences:{days}`，前綴 swd:v1 由 CACHES 設定加上）；
    兩清單皆空回空清單（200）。驗證錯誤 400 {"error": ...}。
    """

    def get(self, request):
        """回傳 {"days": n, "upcoming": [...], "recent": [...]}。"""
        days = _parse_days(request.query_params.get("days"))
        cache_key = f"conferences:{days}"

        payload = cache.get(cache_key)
        if payload is None:
            payload = {
                "days": days,
                "upcoming": selectors.upcoming_conferences(days),
                "recent": selectors.recent_conference_announcements(RECENT_LIMIT),
            }
            cache.set(cache_key, payload, timeout=CACHE_TTL)

        return Response(payload)
