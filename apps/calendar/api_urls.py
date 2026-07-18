"""calendar API URL：GET /api/calendar/summary。"""

from django.urls import path

from .views import CalendarSummaryView

app_name = "calendar_api"

urlpatterns = [
    path("summary", CalendarSummaryView.as_view(), name="summary"),
]
