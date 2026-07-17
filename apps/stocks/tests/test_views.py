"""個股查詢（/stocks/query）頁面殼測試：200、使用模板、Navbar active 邏輯。"""

import re

from django.test import Client

client = Client()

# 擷取帶 active 的 nav 連結及其顯示文字（跨行、寬鬆空白）
ACTIVE_LINK = re.compile(r'class="nav-link active".*?>(.*?)</a>', re.DOTALL)


def test_query_ok_uses_template():
    """GET /stocks/query 回 200 並使用 stocks/query.html 與 base.html。"""
    response = client.get("/stocks/query")
    assert response.status_code == 200
    templates = [t.name for t in response.templates]
    assert "stocks/query.html" in templates
    assert "base.html" in templates


def test_query_navbar_active():
    """查詢頁時 Navbar 僅「查詢個股」為 active。"""
    html = client.get("/stocks/query").content.decode()
    active = ACTIVE_LINK.findall(html)
    assert len(active) == 1
    assert active[0].strip() == "查詢個股"


def test_query_mounts_vue_app():
    """查詢頁（D4）含 Vue 掛載點與 query 進入點資產。"""
    html = client.get("/stocks/query").content.decode()
    assert 'id="stock-query-app"' in html
    assert "src/query.js" in html
