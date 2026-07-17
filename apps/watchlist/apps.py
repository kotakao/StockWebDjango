"""watchlist app（D5）：自選股與持股頁（唯讀呈現 market.db 的 watchlist/holdings）。"""

from django.apps import AppConfig


class WatchlistConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.watchlist"
