"""專案 URL 路由。API 於 /api，頁面殼：首頁（/）、個股查詢（/stocks/）、自選股（/watchlist/）。"""

from django.urls import include, path

urlpatterns = [
    path("api/", include("apps.core.urls")),
    path("api/dashboard/", include("apps.dashboard.api_urls")),
    path("api/stocks/", include("apps.stocks.api_urls")),
    path("api/watchlist/", include("apps.watchlist.api_urls")),
    path("stocks/", include("apps.stocks.urls")),
    path("watchlist/", include("apps.watchlist.urls")),
    path("", include("apps.dashboard.urls")),
]
