"""screener app（D8）：條件選股頁（最新交易日行情＋估值複合篩選）。"""

from django.apps import AppConfig


class ScreenerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.screener"
