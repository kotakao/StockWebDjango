"""專案 URL 路由。API 於 /api，各頁面殼由後續派工（D1+）掛載。"""

from django.urls import include, path

urlpatterns = [
    path("api/", include("apps.core.urls")),
]
