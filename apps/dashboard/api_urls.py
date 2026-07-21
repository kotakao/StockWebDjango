"""dashboard API URL：GET /api/dashboard/summary、GET /api/dashboard/alerts。"""

from django.urls import path

from .views import DashboardAlertsView, DashboardSummaryView

app_name = "dashboard_api"

urlpatterns = [
    path("summary", DashboardSummaryView.as_view(), name="summary"),
    path("alerts", DashboardAlertsView.as_view(), name="alerts"),
]
