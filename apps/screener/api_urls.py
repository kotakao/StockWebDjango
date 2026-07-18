"""screener API URL：GET /api/screener/results。"""

from django.urls import path

from .views import ScreenerResultsView

app_name = "screener_api"

urlpatterns = [
    path("results", ScreenerResultsView.as_view(), name="results"),
]
