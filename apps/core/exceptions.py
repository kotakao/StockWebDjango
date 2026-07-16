"""DRF 統一錯誤格式：一律回 {"error": "<訊息>"}（spec §5）。"""

from rest_framework.views import exception_handler


def _flatten_detail(detail: object) -> str:
    """將 DRF 的錯誤 detail（可能是字串／list／dict）壓平成單一可讀訊息。"""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return "; ".join(_flatten_detail(item) for item in detail)
    if isinstance(detail, dict):
        parts = [f"{key}: {_flatten_detail(value)}" for key, value in detail.items()]
        return "; ".join(parts)
    return str(detail)


def custom_exception_handler(exc, context):
    """呼叫 DRF 預設處理器後，將回應主體統一為 {"error": ...}。

    未被 DRF 捕捉的例外（response is None）維持原行為（交由 Django 回 500）。
    """
    response = exception_handler(exc, context)
    if response is None:
        return None
    detail = response.data.get("detail") if isinstance(response.data, dict) else None
    message = _flatten_detail(detail if detail is not None else response.data)
    response.data = {"error": message}
    return response
