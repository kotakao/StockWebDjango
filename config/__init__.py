"""Django 專案設定套件；匯出 Celery app 以利 shared_task 自動註冊。"""

from .celery import app as celery_app

__all__ = ("celery_app",)
