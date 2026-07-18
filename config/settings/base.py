"""共用設定（base）。

一切環境差異走環境變數（django-environ）；機密與路徑不寫死於程式。
- default：PostgreSQL（DATABASE_URL）；base 提供 SQLite 開發 fallback，prod 強制要求。
- market：SQLite market.db 唯讀（MARKET_DB_PATH），schema 歸 StockDCBot 管理，本專案禁止寫入。
"""

from pathlib import Path

import environ

# 專案根目錄（config/settings/base.py → 上溯三層）
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# 若根目錄存在 .env 則載入（.env 嚴禁提交；見 .env.example）
environ.Env.read_env(BASE_DIR / ".env")

# 機密：base 不提供真實預設值（dev.py 給明確標示的不安全預設；prod.py 強制環境變數）
SECRET_KEY = env("SECRET_KEY", default="")

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# ---- 應用 ----
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_vite",
    "apps.core",
    "apps.market",
    "apps.dashboard",
    "apps.stocks",
    "apps.watchlist",
    "apps.conferences",
    "apps.calendar",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---- 雙資料庫（spec §4）----
DATABASES = {
    # default：PostgreSQL（DATABASE_URL）；base 給 SQLite 開發 fallback，prod.py 強制要求
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'dev-default.sqlite3'}",
    ),
    # market：唯讀 SQLite market.db，schema 由 StockDCBot 獨占；本專案禁寫（Router + PRAGMA 雙保險）
    "market": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env("MARKET_DB_PATH", default=str(BASE_DIR / "market.db")),
        # 唯讀：連線建立後由 apps.market.signals 執行 PRAGMA query_only=ON
        # 測試不對 market 跑 migration（唯讀、managed=False；實際檔案由 conftest fixture 注入）
        "TEST": {"MIGRATE": False},
    },
}

# Database Router：market app 模型 → market 庫、寫入路由 None、allow_migrate=False
DATABASE_ROUTERS = ["config.routers.MarketRouter"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Redis 快取（django-redis）----
REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "swd:v1",  # spec §7：Redis key 版本前綴
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

# ---- Celery（broker/result 皆 redis）----
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ACKS_LATE = True
CELERY_TIMEZONE = "Asia/Taipei"

# ---- 自選股（D5）：對應 market.db watchlist/holdings 的 user_id（Discord 使用者 ID）----
WATCHLIST_USER_ID = env("WATCHLIST_USER_ID", default="0")

# ---- DRF 全域設定（JSON only、anon 60/min、統一 400 錯誤格式）----
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min"},
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "UNAUTHENTICATED_USER": None,
}

# ---- 前端建置（django-vite）----
DJANGO_VITE = {
    "default": {
        "dev_mode": DEBUG,
        "manifest_path": BASE_DIR / "frontend" / "dist" / ".vite" / "manifest.json",
    }
}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "frontend" / "dist"]

LANGUAGE_CODE = "zh-hant"
TIME_ZONE = "Asia/Taipei"
USE_I18N = True
USE_TZ = True

# ---- 日誌（INFO；Celery task 成功/失敗留紀錄）----
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(levelname)s %(name)s %(message)s"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
