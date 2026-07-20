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


class Institutional(models.Model):
    """institutional：三大法人每日買賣超（股數）。PK(market, date, code)。

    foreign_net／trust_net／dealer_net 皆為當日買賣超股數（正買超負賣超），容錯 NULL；
    D10 個股 K 線副圖以三者加總（÷1000 換算張）呈現。本專案唯讀呈現。
    """

    pk = models.CompositePrimaryKey("market", "date", "code")
    market = models.CharField(max_length=8)
    date = models.CharField(max_length=10)
    code = models.CharField(max_length=8)
    name = models.TextField(null=True)
    foreign_net = models.FloatField(null=True)
    trust_net = models.FloatField(null=True)
    dealer_net = models.FloatField(null=True)

    class Meta:
        managed = False
        db_table = "institutional"


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


class Watchlist(models.Model):
    """watchlist：使用者自選股（由 Discord /watch 或 Blazor 版寫入）。PK(user_id, code)。

    user_id 為 Discord 使用者 ID（TEXT）。本專案唯讀呈現，不提供編輯。
    """

    pk = models.CompositePrimaryKey("user_id", "code")
    user_id = models.TextField()
    code = models.CharField(max_length=8)

    class Meta:
        managed = False
        db_table = "watchlist"


class Holding(models.Model):
    """holdings：使用者持股（由 Discord /watch 或 Blazor 版寫入）。PK(user_id, code)。

    shares／avg_cost 容錯 NULL；updated_at 為寫入端維護的字串時間。本專案唯讀呈現。
    """

    pk = models.CompositePrimaryKey("user_id", "code")
    user_id = models.TextField()
    code = models.CharField(max_length=8)
    shares = models.FloatField(null=True)
    avg_cost = models.FloatField(null=True)
    updated_at = models.TextField(null=True)

    class Meta:
        managed = False
        db_table = "holdings"


class InvestorConference(models.Model):
    """investor_conferences：法說會公告（DC-K 每日快照過濾入庫，主旨含「法人說明會」）。

    PK(market, code, announce_date, announce_time)。日期皆 ISO YYYY-MM-DD、時間 HH:MM:SS，
    缺漏容錯 NULL。fact_date 為法說會召開日。本專案唯讀呈現。
    """

    pk = models.CompositePrimaryKey("market", "code", "announce_date", "announce_time")
    market = models.CharField(max_length=8)
    code = models.CharField(max_length=8)
    announce_date = models.CharField(max_length=10)
    announce_time = models.CharField(max_length=8)
    name = models.TextField(null=True)
    subject = models.TextField(null=True)
    matched_clause = models.TextField(null=True)
    fact_date = models.CharField(max_length=10, null=True)
    description = models.TextField(null=True)
    report_date = models.CharField(max_length=10, null=True)

    class Meta:
        managed = False
        db_table = "investor_conferences"


class DividendEvent(models.Model):
    """dividend_events：除權息事件（StockDCBot 功能區 I 入庫）。PK(market, code, ex_date)。

    ex_date 為除權息交易日 ISO YYYY-MM-DD；cash_dividend/stock_ratio 容錯 NULL。
    本專案唯讀呈現。
    """

    pk = models.CompositePrimaryKey("market", "code", "ex_date")
    market = models.CharField(max_length=8)
    code = models.CharField(max_length=8)
    ex_date = models.CharField(max_length=10)
    name = models.TextField(null=True)
    event_type = models.TextField(null=True)
    cash_dividend = models.FloatField(null=True)
    stock_ratio = models.FloatField(null=True)

    class Meta:
        managed = False
        db_table = "dividend_events"


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
