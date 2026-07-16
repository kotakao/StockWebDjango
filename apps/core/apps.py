"""core app 設定：共用例外、回應格式、健康檢查與 debug task。"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
