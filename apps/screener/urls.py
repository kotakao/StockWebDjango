"""screener URL：條件選股頁（/screener）。"""

from django.urls import path

from . import views

app_name = "screener"

urlpatterns = [
    path("", views.index, name="index"),
]
