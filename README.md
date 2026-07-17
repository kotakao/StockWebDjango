# StockWebDjango

台股盤後研究網頁（Django 版）。資料由姊妹專案 **StockDCBot** 於每交易日 17:00 後寫入 SQLite `market.db`；本專案負責查詢、彙整與視覺化。

- 系統規格：[`docs/spec.md`](docs/spec.md)
- 開發派工：[`todolist.md`](todolist.md)
- 行為準則與鐵律：[`AGENT.md`](AGENT.md)

## 技術棧

Python 3.12 / Django 5.2 LTS / DRF / PostgreSQL 16（自有資料）＋ SQLite `market.db`（唯讀）/ Redis＋Celery / Bootstrap 5.3＋Vue 3.5（Vite）/ Lightweight Charts 4.2.3 / Gunicorn＋Nginx / Docker Compose。

## 依賴管理

- **後端**：pip ＋ `requirements.txt`（執行時）／`requirements-dev.txt`（含測試、lint）。每個依賴於檔案內註明用途。
- **前端**：npm ＋ `frontend/package.json`（依賴鎖版；`npm ci` 依 `package-lock.json`）。

## 鐵律（摘要，詳見 AGENT.md／spec §4）

1. `market.db` 的 schema 歸 StockDCBot 獨占；本專案對 `market` 連線嚴禁任何 CREATE/ALTER/DROP/INSERT/UPDATE/DELETE。
2. 唯讀雙保險：連線層 `PRAGMA query_only=ON`（[`apps/market/signals.py`](apps/market/signals.py)）＋ Database Router 封鎖寫入（[`config/routers.py`](config/routers.py)）。有「寫入必失敗」的證明測試。
3. Django 自有資料一律落 PostgreSQL（`default`）。
4. 機密與路徑走環境變數；`.env` 嚴禁提交（見 `.env.example`）。

## 環境變數

複製 `.env.example` 為 `.env` 並填值：

| 變數 | 用途 |
|---|---|
| `SECRET_KEY` | Django 密鑰（正式必改） |
| `ALLOWED_HOSTS` | 允許主機（逗號分隔） |
| `DATABASE_URL` | PostgreSQL 連線字串（`default` 庫） |
| `REDIS_URL` | Redis（快取／Celery） |
| `MARKET_DB_PATH` | `market.db` 路徑（宿主機實體檔；compose 作為 `:ro` 掛載來源） |
| `POSTGRES_USER/PASSWORD/DB` | 僅 compose 的 postgres 服務使用 |

## 啟動方式

### A. 開發（dev profile：容器跑 redis/postgres，宿主機跑 Django）

```bash
# 1) 建立虛擬環境並安裝依賴
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt   # Windows
# source .venv/bin/activate && pip install -r requirements-dev.txt   # macOS/Linux

# 2) 啟動基礎服務（僅 redis + postgres）
docker compose --profile dev up -d

# 3) 建立 default 庫結構並啟動開發伺服器
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py runserver

# 4) 前端（另開終端；HMR 開發模式）
cd frontend && npm install && npm run dev
```

- 健康檢查：<http://127.0.0.1:8000/api/health>（三項連通回 200；任一失敗回 503 與明細）。
- `manage.py` 預設 `DJANGO_SETTINGS_MODULE=config.settings.dev`。

### B. 全套（nginx/web/worker/redis/postgres）

```bash
# 前端建置產物由 Dockerfile 多階段（Node build → Python slim）產出
docker compose --profile full up -d --build
```

- 對外入口：<http://localhost/>（Nginx→web）；`/static/*` 由 Nginx 直接服務。
- `market.db` 以 `MARKET_DB_PATH` 為來源、`:ro` 掛載於容器 `/data/market.db`。

> 註：Compose profile 語意無法讓「plain `docker compose up`」啟動全部、又讓「`--profile dev up`」只啟動子集，故兩情境皆以明確 `--profile` 指定。

## 測試與 lint

```bash
.venv/Scripts/python -m pytest      # 測試（settings=config.settings.test，無需 postgres/redis/docker）
.venv/Scripts/ruff check .          # lint
```

測試以 `config.settings.test` 執行：`default` 用暫時 SQLite、`market` 由 conftest 的 `market_db` fixture 注入暫時檔、Redis 用 fakeredis。含健康檢查、router 路由、以及「market 寫入必失敗」鐵律證明測試。

## 功能：查詢個股

導覽列「查詢個股」（`/stocks/query`）為個股近期資料頁（派工 D4）。

- **輸入**：股票代號（前端先驗 4-6 位英數）→ 按「查詢」，呼叫 `GET /api/stocks/{code}/summary`。
- **彙整中**：快照尚未就緒時 API 回 `202`，頁面顯示「彙整中…」並以 1 秒間隔輪詢（上限 10 次）；逾時顯示提示與「重試」按鈕。
- **錯誤**：代號格式錯或查無代號回 `400`，頁面顯示 API 錯誤訊息。
- **結果（200）**：
  - 指標卡列：收盤與漲跌%（紅漲綠跌，台股慣例）、本益比、股價淨值比、殖利率、月營收 YoY、累計營收 YoY、毛利率、營業利益率、EPS；每卡標註資料基準（交易日／營收月份／財報季），數值缺漏顯示「—」。
  - 近期資料表：近 20 個交易日快照（日期、收盤、漲跌%、PE、PB、殖利率）。

> 前端為每頁獨立 Vue app（[`frontend/components/StockQuery.vue`](frontend/components/StockQuery.vue)，進入點 [`frontend/src/query.js`](frontend/src/query.js)）；僅取數渲染，商業邏輯在後端。

## 前端建置

```bash
cd frontend
npm install
npm run dev     # 開發（Vite HMR，port 5173）
npm run build   # 產出 dist/（含 manifest，供 django-vite 注入）
```

## 專案結構

```
config/            # settings 分層（base/dev/prod/test）、urls、wsgi/asgi、celery、routers
apps/
  core/            # 健康檢查、DRF 統一錯誤格式、debug task
  market/          # market.db 唯讀存取層：managed=False 模型 + 唯讀 signal
  dashboard/       # D2（空殼）
  stocks/          # D3/D4（空殼）
frontend/          # Vite + Vue3 + Bootstrap + lightweight-charts
templates/         # base.html（Navbar 佔位）
docker/nginx/      # nginx 反向代理設定
```
