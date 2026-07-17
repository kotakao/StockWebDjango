"""自選股（/watchlist）頁面殼測試：200、使用模板、Navbar active、Vue 掛載與唯讀註記。"""

import re

from django.test import Client

client = Client()

# 擷取帶 active 的 nav 連結及其顯示文字（跨行、寬鬆空白）
ACTIVE_LINK = re.compile(r'class="nav-link active".*?>(.*?)</a>', re.DOTALL)


def test_watchlist_ok_uses_template():
    """GET /watchlist/ 回 200 並使用 watchlist/index.html 與 base.html。"""
    response = client.get("/watchlist/")
    assert response.status_code == 200
    templates = [t.name for t in response.templates]
    assert "watchlist/index.html" in templates
    assert "base.html" in templates


def test_watchlist_navbar_active():
    """自選股頁時 Navbar 僅「自選股」為 active。"""
    html = client.get("/watchlist/").content.decode()
    active = ACTIVE_LINK.findall(html)
    assert len(active) == 1
    assert active[0].strip() == "自選股"


def test_watchlist_mounts_vue_app():
    """自選股頁含 Vue 掛載點與 watchlist 進入點資產。"""
    html = client.get("/watchlist/").content.decode()
    assert 'id="watchlist-app"' in html
    assert "src/watchlist.js" in html
