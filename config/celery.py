"""Celery 應用設定；broker/result = Redis，設定自 Django settings 的 CELERY_ 命名空間讀取。"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("stockwebdjango")
# 由 Django settings 讀取 CELERY_ 前綴設定
app.config_from_object("django.conf:settings", namespace="CELERY")
# 自動探索各 app 的 tasks.py
app.autodiscover_tasks()
