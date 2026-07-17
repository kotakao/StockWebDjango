"""conferences URL：法說會頁（/conferences）。"""

from django.urls import path

from . import views

app_name = "conferences"

urlpatterns = [
    path("", views.index, name="index"),
]
