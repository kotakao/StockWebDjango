"""core Celery tasks：debug task 供環境驗證。"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def debug_task() -> str:
    """最小可用 task：留 log 並回傳固定字串，供 Celery 連通性驗證。"""
    logger.info("core.debug_task 執行成功")
    return "ok"
