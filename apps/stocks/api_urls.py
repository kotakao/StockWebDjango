"""stocks API URL：GET /api/stocks/{code}/summary。"""

from django.urls import path

from .views import StockRevenueView, StockSummaryView

app_name = "stocks_api"

urlpatterns = [
    path("<str:code>/summary", StockSummaryView.as_view(), name="summary"),
    path("<str:code>/revenue", StockRevenueView.as_view(), name="revenue"),
]
