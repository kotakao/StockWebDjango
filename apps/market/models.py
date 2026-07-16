"""market.db 唯讀存取層：managed=False 模型，欄位對照 StockDCBot storage.py 的 CREATE TABLE。

鐵律：本專案對這些表嚴禁任何 DDL/DML；schema 歸 StockDCBot 獨占管理。
所有數值欄位（REAL）容錯 NULL；主鍵沿用 SQLite 的複合鍵（Django 5.2 CompositePrimaryKey）。
"""

from django.db import models


class DailyQuote(models.Model):
    """daily_quotes：個股每日行情。PK(market, date, code)。"""

    pk = models.CompositePrimaryKey("market", "date", "code")
    market = models.CharField(max_length=8)
    date = models.CharField(max_length=10)
    code = models.CharField(max_length=8)
    name = models.TextField(null=True)
    open = models.FloatField(null=True)
    high = models.FloatField(null=True)
    low = models.FloatField(null=True)
    close = models.FloatField(null=True)
    change = models.FloatField(null=True)
    volume = models.FloatField(null=True)

    class Meta:
        managed = False
        db_table = "daily_quotes"


class Valuation(models.Model):
    """valuation：本益比／殖利率／股價淨值比。PK(market, date, code)。"""

    pk = models.CompositePrimaryKey("market", "date", "code")
    market = models.CharField(max_length=8)
    date = models.CharField(max_length=10)
    code = models.CharField(max_length=8)
    pe = models.FloatField(null=True)
    dividend_yield = models.FloatField(null=True)
    pb = models.FloatField(null=True)

    class Meta:
        managed = False
        db_table = "valuation"


class MarketDaily(models.Model):
    """market_daily：市場層級每日彙整。PK(market, date)。"""

    pk = models.CompositePrimaryKey("market", "date")
    market = models.CharField(max_length=8)
    date = models.CharField(max_length=10)
    index_close = models.FloatField(null=True)
    index_change_pct = models.FloatField(null=True)
    turnover = models.FloatField(null=True)
    up_count = models.FloatField(null=True)
    down_count = models.FloatField(null=True)
    foreign_net = models.FloatField(null=True)
    trust_net = models.FloatField(null=True)
    dealer_net = models.FloatField(null=True)
    margin_balance = models.FloatField(null=True)
    short_balance = models.FloatField(null=True)

    class Meta:
        managed = False
        db_table = "market_daily"


class MonthlyRevenue(models.Model):
    """monthly_revenue：月營收。PK(market, code, year_month)。"""

    pk = models.CompositePrimaryKey("market", "code", "year_month")
    market = models.CharField(max_length=8)
    code = models.CharField(max_length=8)
    year_month = models.CharField(max_length=7)
    name = models.TextField(null=True)
    revenue = models.FloatField(null=True)
    mom_pct = models.FloatField(null=True)
    yoy_pct = models.FloatField(null=True)
    cum_revenue = models.FloatField(null=True)
    cum_yoy_pct = models.FloatField(null=True)

    class Meta:
        managed = False
        db_table = "monthly_revenue"


class QuarterlyFinancial(models.Model):
    """quarterly_financials：季度損益。PK(market, code, year_quarter)。"""

    pk = models.CompositePrimaryKey("market", "code", "year_quarter")
    market = models.CharField(max_length=8)
    code = models.CharField(max_length=8)
    year_quarter = models.CharField(max_length=6)
    name = models.TextField(null=True)
    revenue = models.FloatField(null=True)
    gross_profit = models.FloatField(null=True)
    operating_income = models.FloatField(null=True)
    net_income = models.FloatField(null=True)
    eps = models.FloatField(null=True)

    class Meta:
        managed = False
        db_table = "quarterly_financials"
