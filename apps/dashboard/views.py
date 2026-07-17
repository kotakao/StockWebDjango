"""dashboard 頁面殼（D1）：首頁儀表板。內容圖卡於 D2 實作。"""

from django.shortcuts import render


def index(request):
    """首頁儀表板頁面殼，繼承 base.html，內容區為佔位卡片。"""
    return render(request, "dashboard/index.html")
