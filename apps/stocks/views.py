"""stocks 頁面殼（D1）：個股查詢。查詢邏輯於 D4 實作。"""

from django.shortcuts import render


def query(request):
    """個股查詢頁面殼，繼承 base.html，內容區為佔位表單。"""
    return render(request, "stocks/query.html")
