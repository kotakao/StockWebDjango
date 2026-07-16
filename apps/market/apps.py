"""market app 設定：載入唯讀連線 signal。"""

from django.apps import AppConfig


class MarketConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.market"

    def ready(self) -> None:
        """連接 connection_created signal，對 market 連線施加 PRAGMA query_only。"""
        from . import signals  # noqa: F401  匯入即註冊 signal receiver
