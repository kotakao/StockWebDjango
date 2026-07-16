"""正式設定（prod）。

安全基線：DEBUG=False、SECRET_KEY 唯環境變數、ALLOWED_HOSTS 明列、
default 強制 PostgreSQL、django-vite 走 build 產物。
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# 唯環境變數，缺少即啟動失敗（不提供任何預設）
SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# default 強制 PostgreSQL（DATABASE_URL 必填）
DATABASES["default"] = env.db("DATABASE_URL")  # noqa: F405

# django-vite 走建置產物（manifest）；沿用 base 的 manifest_path
DJANGO_VITE = {
    "default": {
        "dev_mode": False,
        "manifest_path": BASE_DIR / "frontend" / "dist" / ".vite" / "manifest.json",  # noqa: F405
    }
}

# 安全 headers（Nginx 另補；此處為應用層基線）
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
