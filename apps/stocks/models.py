"""stocks 自有資料模型（spec §4.3）：stock_snapshots。

鐵律：本表為 Django 自有資料，一律落 default（PostgreSQL）庫，嚴禁建入 market.db。
一檔股票每交易日一列（unique(code, trade_date)）；全欄位容錯 NULL（來源缺漏不阻斷）。
數值以 FloatField（對齊 market 模型與 JSON 數值輸出；避免 Decimal 序列化為字串）。
"""

from django.db import models


class StockSnapshot(models.Model):
    """個股單日快照：自 market.db 既有表彙整而來的指標（spec §4.3）。"""

    code = models.CharField(max_length=8)
    name = models.TextField(null=True)
    market = models.CharField(max_length=8, null=True)
    trade_date = models.DateField()

    close = models.FloatField(null=True)
    change_pct = models.FloatField(null=True)

    pe = models.FloatField(null=True)
    pb = models.FloatField(null=True)
    dividend_yield = models.FloatField(null=True)

    revenue_yoy = models.FloatField(null=True)
    revenue_cum_yoy = models.FloatField(null=True)
    revenue_month = models.CharField(max_length=7, null=True)

    gross_margin = models.FloatField(null=True)
    operating_margin = models.FloatField(null=True)
    eps = models.FloatField(null=True)
    quarter = models.CharField(max_length=6, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock_snapshots"
        constraints = [
            models.UniqueConstraint(
                fields=["code", "trade_date"], name="uniq_stock_snapshot_code_date"
            )
        ]
        indexes = [models.Index(fields=["code", "-trade_date"])]

    def __str__(self) -> str:
        return f"{self.code}@{self.trade_date}"
