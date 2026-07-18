"""行事曆（/calendar）頁面殼測試：200、使用模板、Navbar active、Vue 掛載點與進入點。"""

import re

from django.test import Client

client = Client()

# 擷取帶 active 的 nav 連結及其顯示文字（跨行、寬鬆空白）
ACTIVE_LINK = re.compile(r'class="nav-link active".*?>(.*?)</a>', re.DOTALL)


def test_calendar_ok_uses_template():
    """GET /calendar/ 回 200 並使用 calendar/index.html 與 base.html。"""
    response = client.get("/calendar/")
    assert response.status_code == 200
    templates = [t.name for t in response.templates]
    assert "calendar/index.html" in templates
    assert "base.html" in templates


def test_calendar_navbar_active():
    """行事曆頁時 Navbar 僅「行事曆」為 active。"""
    html = client.get("/calendar/").content.decode()
    active = ACTIVE_LINK.findall(html)
    assert len(active) == 1
    assert active[0].strip() == "行事曆"


def test_calendar_mounts_vue_app():
    """行事曆頁含 Vue 掛載點與 calendar 進入點資產。"""
    html = client.get("/calendar/").content.decode()
    assert 'id="calendar-app"' in html
    assert "src/calendar.js" in html
