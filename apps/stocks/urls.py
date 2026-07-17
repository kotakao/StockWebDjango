"""stocks URL：個股查詢（/stocks/query）。"""

from django.urls import path

from . import views

app_name = "stocks"

urlpatterns = [
    path("query", views.query, name="query"),
]
