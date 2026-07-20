"""stocks API URL：GET /api/stocks/{code}/summary。"""

from django.urls import path

from .views import StockQuotesView, StockRevenueView, StockSummaryView

app_name = "stocks_api"

urlpatterns = [
    path("<str:code>/summary", StockSummaryView.as_view(), name="summary"),
    path("<str:code>/revenue", StockRevenueView.as_view(), name="revenue"),
    path("<str:code>/quotes", StockQuotesView.as_view(), name="quotes"),
]
