"""core 端點：GET /api/health 健康檢查（default DB／market DB／Redis 連通）。"""

from django.db import connections
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


def _check_database(alias: str) -> tuple[bool, str]:
    """對指定 DB 連線執行 SELECT 1，回 (是否成功, 訊息)。"""
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True, "ok"
    except Exception as exc:  # noqa: BLE001  健康檢查需回報任何連線錯誤
        return False, str(exc)


def _check_redis() -> tuple[bool, str]:
    """對 Redis 執行 PING，回 (是否成功, 訊息)。"""
    try:
        get_redis_connection("default").ping()
        return True, "ok"
    except Exception as exc:  # noqa: BLE001  健康檢查需回報任何連線錯誤
        return False, str(exc)


class HealthView(APIView):
    """健康檢查：全部連通回 200，任一失敗回 503 與各項明細。"""

    # 健康檢查供容器 healthcheck 高頻呼叫，不套用匿名節流
    throttle_classes: list = []

    def get(self, request):
        """檢查 default DB、market DB、Redis 三者連通性。"""
        default_ok, default_msg = _check_database("default")
        market_ok, market_msg = _check_database("market")
        redis_ok, redis_msg = _check_redis()

        checks = {
            "default_db": {"ok": default_ok, "detail": default_msg},
            "market_db": {"ok": market_ok, "detail": market_msg},
            "redis": {"ok": redis_ok, "detail": redis_msg},
        }
        all_ok = default_ok and market_ok and redis_ok
        code = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response({"status": "ok" if all_ok else "error", "checks": checks}, status=code)
