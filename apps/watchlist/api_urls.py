"""watchlist API URL：GET /api/watchlist/summary。"""

from django.urls import path

from .views import WatchlistSummaryView

app_name = "watchlist_api"

urlpatterns = [
    path("summary", WatchlistSummaryView.as_view(), name="summary"),
]
