"""健康檢查端點測試：全部連通回 200、任一失敗回 503。"""

from rest_framework.test import APIClient

client = APIClient()


def test_health_ok(market_db):
    """default DB／market DB／Redis 皆連通時回 200 且各項 ok。"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["default_db"]["ok"] is True
    assert data["checks"]["market_db"]["ok"] is True
    assert data["checks"]["redis"]["ok"] is True


def test_health_reports_failure(market_db, monkeypatch):
    """Redis 不通時回 503，並在明細標示 redis 失敗。"""

    def _boom(*args, **kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr("apps.core.views.get_redis_connection", _boom)

    response = client.get("/api/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["checks"]["redis"]["ok"] is False
