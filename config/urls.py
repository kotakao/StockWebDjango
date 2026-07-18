"""專案 URL 路由。

API 於 /api；頁面殼：首頁（/）、個股查詢（/stocks/）、自選股（/watchlist/）、
法說會（/conferences/）。
"""

from django.urls import include, path

urlpatterns = [
    path("api/", include("apps.core.urls")),
    path("api/dashboard/", include("apps.dashboard.api_urls")),
    path("api/stocks/", include("apps.stocks.api_urls")),
    path("api/watchlist/", include("apps.watchlist.api_urls")),
    path("api/conferences/", include("apps.conferences.api_urls")),
    path("api/calendar/", include("apps.calendar.api_urls")),
    path("api/screener/", include("apps.screener.api_urls")),
    path("stocks/", include("apps.stocks.urls")),
    path("watchlist/", include("apps.watchlist.urls")),
    path("conferences/", include("apps.conferences.urls")),
    path("calendar/", include("apps.calendar.urls")),
    path("screener/", include("apps.screener.urls")),
    path("", include("apps.dashboard.urls")),
]
