"""首頁（/）頁面殼測試：200、使用模板、Navbar active 邏輯。"""

import re

from django.test import Client

client = Client()

# 擷取帶 active 的 nav 連結及其顯示文字（跨行、寬鬆空白）
ACTIVE_LINK = re.compile(r'class="nav-link active".*?>(.*?)</a>', re.DOTALL)


def test_index_ok_uses_template():
    """GET / 回 200 並使用 dashboard/index.html 與 base.html。"""
    response = client.get("/")
    assert response.status_code == 200
    templates = [t.name for t in response.templates]
    assert "dashboard/index.html" in templates
    assert "base.html" in templates


def test_index_navbar_home_active():
    """首頁時 Navbar 僅「首頁」為 active。"""
    html = client.get("/").content.decode()
    active = ACTIVE_LINK.findall(html)
    assert len(active) == 1
    assert active[0].strip() == "首頁"
