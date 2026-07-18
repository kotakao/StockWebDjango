"""calendar 頁面殼與行事曆 API（D7）。

- index：行事曆頁面殼（掛載 Vue app）。
- CalendarSummaryView：GET /api/calendar/summary?month=YYYY-MM，唯讀彙整＋Redis 快取。

純唯讀呈現 market.db 的 dividend_events（功能區 I 入庫）與 investor_conferences（DC-K）；
無商業邏輯（月份→日期窗＋兩次唯讀查詢＋組裝信封），故不設 services 層。月曆組格屬前端邏輯。
"""

import calendar
from datetime import date

from django.core.cache import cache
from django.shortcuts import render
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market import selectors

YEAR_MIN = 2020
YEAR_MAX = 2099
CACHE_TTL = 600  # 10 分鐘（spec §7）


def index(request):
    """行事曆頁面殼，繼承 base.html，內容由 Vue app 渲染。"""
    return render(request, "calendar/index.html")


def _parse_month(raw: str | None) -> str:
    """驗證 month 參數：YYYY-MM 且年份 2020~2099，預設當月；不合法拋 ValidationError（→400）。"""
    if raw is None or raw == "":
        return date.today().strftime("%Y-%m")
    try:
        parsed = date.fromisoformat(f"{raw}-01")
    except (TypeError, ValueError):
        raise ValidationError("month 格式須為 YYYY-MM") from None
    if not (YEAR_MIN <= parsed.year <= YEAR_MAX):
        raise ValidationError(f"month 年份需介於 {YEAR_MIN} 與 {YEAR_MAX}")
    # 標準化（例如去掉多餘字元）：以解析結果回填，確保 key 一致。
    return f"{parsed.year:04d}-{parsed.month:02d}"


class CalendarSummaryView(APIView):
    """行事曆彙整：某月除權息（dividend_events）與法說會（investor_conferences）日期。

    整包回應以 Redis 快取（key `calendar:{month}`，前綴 swd:v1 由 CACHES 設定加上）；
    兩清單皆空回空清單（200）。驗證錯誤 400 {"error": ...}。
    """

    def get(self, request):
        """回傳 {"month": "YYYY-MM", "dividends": [...], "conferences": [...]}。"""
        month = _parse_month(request.query_params.get("month"))
        cache_key = f"calendar:{month}"

        payload = cache.get(cache_key)
        if payload is None:
            year, mon = int(month[:4]), int(month[5:7])
            start = f"{month}-01"
            end = f"{month}-{calendar.monthrange(year, mon)[1]:02d}"
            payload = {
                "month": month,
                "dividends": selectors.dividend_events_between(start, end),
                "conferences": selectors.conference_dates_between(start, end),
            }
            cache.set(cache_key, payload, timeout=CACHE_TTL)

        return Response(payload)
