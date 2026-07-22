"""stocks 自有資料模型（spec §4.3、D13）：stock_snapshots、company_research、research_theme。

鐵律：本檔各表為 Django 自有資料，一律落 default（PostgreSQL）庫，嚴禁建入 market.db。
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


class CompanyResearch(models.Model):
    """公司質化研究資料（D13）：自 My-TW-Coverage 匯入的業務簡介與題材歸屬。

    - 第三方 LLM 研究資料（非權威、非即時），僅取質化層；財務/估值不匯入。
    - code 對應 market 的股票代號，跨庫不建 FK。
    - themes：題材 slug 陣列。規格原訂 ArrayField（PostgreSQL 專屬），但
      config.settings.test 的 default 庫為 SQLite，故改用 JSONField（跨庫皆可、
      語意同為 list；本任務查詢僅以 code 取列，無需 contains 查詢）。
    """

    code = models.CharField(max_length=8, primary_key=True)
    name = models.CharField(max_length=64, blank=True, default="")
    sector_en = models.CharField(max_length=64, blank=True, default="")
    industry_en = models.CharField(max_length=64, blank=True, default="")
    business_summary = models.TextField(blank=True, default="")
    themes = models.JSONField(default=list)
    source_repo = models.CharField(max_length=128, default="Timeverse/My-TW-Coverage")
    source_commit = models.CharField(max_length=40, blank=True, default="")
    imported_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "company_research"
        indexes = [models.Index(fields=["sector_en"])]

    def __str__(self) -> str:
        return f"{self.code} {self.name}"


class ResearchTheme(models.Model):
    """題材（D13）：My-TW-Coverage themes/*.md 的題材定義。

    成員關係存於 CompanyResearch.themes 陣列（不建 M2M 中間表）。
    """

    key = models.CharField(max_length=64, primary_key=True)
    title = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "research_theme"

    def __str__(self) -> str:
        return f"{self.key}: {self.title}"
