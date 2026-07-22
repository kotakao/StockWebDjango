"""dashboard 頁面殼與儀表板 API（D2）。

- index：首頁頁面殼（掛載 Vue app）。
- DashboardSummaryView：GET /api/dashboard/summary?days=60，market_daily 序列＋Redis 快取。
"""

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.params import parse_bounded_int
from apps.market import selectors

from .services import build_dashboard_summary, collect_recent_alerts

DAYS_DEFAULT = 60
DAYS_MIN = 1
DAYS_MAX = 252
CACHE_TTL = 600  # 10 分鐘（spec §7）

ALERTS_DAYS_DEFAULT = 5
ALERTS_DAYS_MIN = 1
ALERTS_DAYS_MAX = 10


def index(request):
    """首頁儀表板頁面殼，繼承 base.html，內容由 Vue app 渲染。"""
    return render(request, "dashboard/index.html")


class DashboardSummaryView(APIView):
    """市場序列彙整：指數、成交金額、漲跌家數、三大法人、融資餘額。

    整包回應以 Redis 快取（key `dashboard:{days}`，前綴 swd:v1 由 CACHES 設定加上）；
    快取命中則不重查 market 庫。
    """

    def get(self, request):
        """回傳近 days 交易日的四序列；驗證錯誤 400 {"error": ...}。"""
        days = parse_bounded_int(
            request.query_params.get("days"), default=DAYS_DEFAULT, lo=DAYS_MIN, hi=DAYS_MAX
        )
        cache_key = f"dashboard:{days}"

        payload = cache.get(cache_key)
        if payload is None:
            rows = selectors.recent_market_daily(days)
            payload = build_dashboard_summary(rows, days)
            cache.set(cache_key, payload, timeout=CACHE_TTL)

        return Response(payload)


class DashboardAlertsView(APIView):
    """近期市場警示：讀 StockDCBot reports JSON 的 sections.market_alerts（D12）。

    純檔案讀取，不觸及 market 資料庫連線。整包回應以 Redis 快取
    （key `alerts:{days}`，前綴 swd:v1 由 CACHES 設定加上），TTL 10 分鐘。
    """

    def get(self, request):
        """回傳最近 days 個交易日的市場警示；驗證錯誤 400 {"error": ...}。

        REPORTS_DIR 未設定／無可讀報告 → 200 {"alerts": [], "reason": "..."}；
        有可讀報告但無警示 → {"alerts": [], "reason": null}。
        """
        days = parse_bounded_int(
            request.query_params.get("days"),
            default=ALERTS_DAYS_DEFAULT, lo=ALERTS_DAYS_MIN, hi=ALERTS_DAYS_MAX,
        )
        cache_key = f"alerts:{days}"

        payload = cache.get(cache_key)
        if payload is None:
            alerts, reason = collect_recent_alerts(settings.REPORTS_DIR, days)
            payload = {"alerts": alerts, "reason": reason}
            cache.set(cache_key, payload, timeout=CACHE_TTL)

        return Response(payload)
