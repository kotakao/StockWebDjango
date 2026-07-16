"""測試設定（test）。

讓測試在無 PostgreSQL／無 Redis／無 Docker 的環境也能全綠：
- default：暫時 SQLite（pytest-django 自建測試庫）。
- market：base 的 SQLite market 連線；實際檔案由 conftest 的 market_db fixture 注入。
- 快取：django-redis 指向 fakeredis（真正走 redis 協定的 ping，但不需 redis server）。
- Celery：eager 模式，task 同步執行便於測試。
"""

import fakeredis

from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = "django-insecure-test-key"  # noqa: S105  測試專用
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# default 用暫時 SQLite，避免測試依賴 PostgreSQL
DATABASES["default"] = {  # noqa: F405
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}

# 快取：django-redis + fakeredis，get_redis_connection().ping() 可真實回應
CACHES = {  # noqa: F811
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/0",
        "KEY_PREFIX": "swd:v1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"connection_class": fakeredis.FakeRedisConnection},
        },
    }
}

# Celery 同步執行，例外直接拋出
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
