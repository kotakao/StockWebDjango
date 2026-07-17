"""watchlist URL：自選股頁（/watchlist）。"""

from django.urls import path

from . import views

app_name = "watchlist"

urlpatterns = [
    path("", views.index, name="index"),
]
