"""market 連線唯讀化（spec §4.2 鐵律，雙保險之連線層）。

每當 market 連線建立，執行 PRAGMA query_only=ON，使任何寫入（DDL/DML）失敗。
與 config.routers.MarketRouter 的寫入封鎖共同構成雙保險。
"""

from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def enforce_market_readonly(sender, connection, **kwargs) -> None:
    """對 market 別名的 SQLite 連線施加 query_only，寫入將回 readonly database 錯誤。"""
    if connection.alias == "market" and connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA query_only = ON;")
