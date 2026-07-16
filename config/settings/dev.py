"""開發設定（dev）。

搭配 compose 的 dev profile：容器跑 redis/postgres，宿主機 runserver。
DATABASE_URL / REDIS_URL / MARKET_DB_PATH 由 .env 提供。
"""

from .base import *  # noqa: F401,F403
from .base import env  # noqa: F401  (供本模組讀取環境變數)

DEBUG = True

# 明確標示的「不安全」開發預設值；正式環境絕不使用（prod.py 強制環境變數）
SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-key-change-me")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# django-vite 開發模式：走 Vite dev server（HMR），不需 build 產物 manifest
DJANGO_VITE = {"default": {"dev_mode": True, "dev_server_port": 5173}}
