"""conferences API URL：GET /api/conferences/summary。"""

from django.urls import path

from .views import ConferenceSummaryView

app_name = "conferences_api"

urlpatterns = [
    path("summary", ConferenceSummaryView.as_view(), name="summary"),
]
