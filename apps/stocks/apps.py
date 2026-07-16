"""stocks app（D3/D4 實作）：stock_snapshots 模型、彙整 services、Celery tasks、查詢 API。

目前為空殼註冊。
"""

from django.apps import AppConfig


class StocksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.stocks"
