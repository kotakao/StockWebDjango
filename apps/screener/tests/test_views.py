"""條件選股（/screener）頁面殼測試：200、使用模板、Navbar active、Vue 掛載點與進入點。"""

import re

from django.test import Client

client = Client()

# 擷取帶 active 的 nav 連結及其顯示文字（跨行、寬鬆空白）
ACTIVE_LINK = re.compile(r'class="nav-link active".*?>(.*?)</a>', re.DOTALL)


def test_screener_ok_uses_template():
    """GET /screener/ 回 200 並使用 screener/index.html 與 base.html。"""
    response = client.get("/screener/")
    assert response.status_code == 200
    templates = [t.name for t in response.templates]
    assert "screener/index.html" in templates
    assert "base.html" in templates


def test_screener_navbar_active():
    """條件選股頁時 Navbar 僅「選股」為 active。"""
    html = client.get("/screener/").content.decode()
    active = ACTIVE_LINK.findall(html)
    assert len(active) == 1
    assert active[0].strip() == "選股"


def test_screener_mounts_vue_app():
    """條件選股頁含 Vue 掛載點與 screener 進入點資產。"""
    html = client.get("/screener/").content.decode()
    assert 'id="screener-app"' in html
    assert "src/screener.js" in html
