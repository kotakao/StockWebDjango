"""法說會（/conferences）頁面殼測試：200、使用模板、Navbar active、Vue 掛載點與進入點。"""

import re

from django.test import Client

client = Client()

# 擷取帶 active 的 nav 連結及其顯示文字（跨行、寬鬆空白）
ACTIVE_LINK = re.compile(r'class="nav-link active".*?>(.*?)</a>', re.DOTALL)


def test_conferences_ok_uses_template():
    """GET /conferences/ 回 200 並使用 conferences/index.html 與 base.html。"""
    response = client.get("/conferences/")
    assert response.status_code == 200
    templates = [t.name for t in response.templates]
    assert "conferences/index.html" in templates
    assert "base.html" in templates


def test_conferences_navbar_active():
    """法說會頁時 Navbar 僅「法說會」為 active。"""
    html = client.get("/conferences/").content.decode()
    active = ACTIVE_LINK.findall(html)
    assert len(active) == 1
    assert active[0].strip() == "法說會"


def test_conferences_mounts_vue_app():
    """法說會頁含 Vue 掛載點與 conferences 進入點資產。"""
    html = client.get("/conferences/").content.decode()
    assert 'id="conferences-app"' in html
    assert "src/conferences.js" in html
