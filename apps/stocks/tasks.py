"""stocks Celery tasks（spec §7）：非同步彙整並 upsert 個股快照。

refresh_snapshot(code)：build_snapshot → upsert stock_snapshots（code+trade_date 冪等）→
失效 Redis swd:v1:stock:{code}。同代號以 Redis lock 防併發重算；失敗可重試 max_retries=3，
成功／失敗皆留 log。
"""

import logging

from celery import shared_task
from django.core.cache import cache

from .models import StockSnapshot
from .services import build_snapshot

logger = logging.getLogger(__name__)

LOCK_TTL = 30  # 秒：單代號重算的鎖存活上限（逾時自動釋放，避免死鎖）
LOCK_KEY = "lock:stock:{code}"  # 前綴 swd:v1 由 CACHES 設定加上
CACHE_KEY = "stock:{code}"


@shared_task(bind=True, max_retries=3)
def refresh_snapshot(self, code: str) -> str:
    """彙整並 upsert 某代號最新快照，成功後主動失效其 Redis 快取。

    以 Redis SET NX（cache.add）作單代號鎖防併發重算：取不到鎖即略過本次。
    回傳字串狀態（供 result backend / 測試判讀）：
    - "locked"：同代號正在重算，本次略過。
    - "not_found"：查無代號，不寫入。
    - "updated"：已 upsert 並失效快取。
    失敗（例外）則以 self.retry 重試（max_retries=3），逾上限拋出。
    """
    lock_key = LOCK_KEY.format(code=code)
    if not cache.add(lock_key, "1", timeout=LOCK_TTL):
        logger.info("refresh_snapshot: %s 已有重算進行中，略過本次", code)
        return "locked"

    try:
        data = build_snapshot(code)
        if data is None:
            logger.warning("refresh_snapshot: 查無代號 %s，不寫入", code)
            return "not_found"

        trade_date = data.pop("trade_date")
        data.pop("code", None)
        StockSnapshot.objects.update_or_create(
            code=code, trade_date=trade_date, defaults=data
        )
        cache.delete(CACHE_KEY.format(code=code))
        logger.info("refresh_snapshot: %s 已更新，trade_date=%s", code, trade_date)
        return "updated"
    except Exception as exc:  # noqa: BLE001  彙整/寫入失敗一律留 log 並重試
        logger.exception("refresh_snapshot: %s 失敗，準備重試", code)
        raise self.retry(exc=exc) from exc
    finally:
        cache.delete(lock_key)
