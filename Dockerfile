# syntax=docker/dockerfile:1

# ---- Stage 1：前端建置（Node 22 → Vite build 產出 dist）----
FROM node:22-slim AS frontend
WORKDIR /build/frontend
# 先複製鎖檔以善用 layer cache
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# ---- Stage 2：Python 執行環境（3.12-slim，非 root，collectstatic）----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# 系統依賴：psycopg 執行期需 libpq；curl 供 healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 應用程式碼
COPY . .
# 帶入前端建置產物（供 collectstatic 收集）
COPY --from=frontend /build/frontend/dist ./frontend/dist

# collectstatic（build 時以佔位環境變數執行，不連線 DB）
RUN SECRET_KEY=build-only \
    DATABASE_URL=sqlite:////tmp/build.sqlite3 \
    ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

# 非 root 執行
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 預設啟動 Gunicorn（compose 的 web 服務會覆寫為含 collectstatic 的啟動指令）
CMD ["gunicorn", "config.wsgi:application", \
     "--workers", "2", "--threads", "2", "--timeout", "60", \
     "--bind", "0.0.0.0:8000"]
