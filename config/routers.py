"""Database Router：market app 的唯讀路由與寫入封鎖（spec §4.2 鐵律）。"""


class MarketRouter:
    """將 market app 模型導向 market 庫，並封鎖對其寫入與 migrate。

    雙保險之一（另一為連線層 PRAGMA query_only=ON，見 apps.market.signals）：
    - 讀取：market app 模型 → market 庫。
    - 寫入：market app 模型 → None（無合法目標，寫入即失敗）。
    - migrate：market app 不 migrate；任何 app 皆不得 migrate 進 market 庫。
    """

    market_app_label = "market"
    market_db_alias = "market"

    def db_for_read(self, model, **hints):
        """market app 模型讀取路由至 market 庫，其餘用預設。"""
        if model._meta.app_label == self.market_app_label:
            return self.market_db_alias
        return None

    def db_for_write(self, model, **hints):
        """market app 模型無合法寫入目標，回 None 封鎖寫入。"""
        if model._meta.app_label == self.market_app_label:
            return None
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """不限制關聯（本專案 market 與 default 不建跨庫關聯）。"""
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """market app 不 migrate；亦不允許任何 app migrate 進 market 庫。"""
        if app_label == self.market_app_label:
            return False
        if db == self.market_db_alias:
            return False
        return None
