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
| `MARKET_DB_PATH` | `market.db` 路徑（宿主機 runserver 使用；唯讀由連線層 `query_only`＋Router 保證） |
| `MARKET_DB_DIR` | `market.db` 所在目錄（僅 compose 掛載用：WAL 讀取需在同目錄建 `-wal`/`-shm`，故掛目錄且可寫） |
| `WATCHLIST_USER_ID` | 自選股/持股頁對應的 Discord 使用者 ID（對應 `market.db` watchlist/holdings 的 `user_id`，預設 `0`） |
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
- `market.db` 以 `MARKET_DB_DIR`（所在目錄）掛載於容器 `/data`（容器內路徑仍為 `/data/market.db`）。掛目錄且可寫是因 SQLite WAL 讀取需在同目錄建 `-wal`/`-shm` 輔助檔（檔案掛載 `:ro` 與 WAL 不相容）；唯讀保證在連線層（`PRAGMA query_only`＋Database Router 雙保險），非檔案系統層。

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
  - 月營收對比表（派工 D9）：summary 就緒後併行呼叫 `GET /api/stocks/{code}/revenue`，列出該代號於 `monthly_revenue` 的**全部**月份（新到舊）：月份、營收（億元＝千元÷100000，兩位小數）、月增%、年增%、累計營收（億元）、累計年增%；NULL 顯示「—」，年增率紅正綠負（台股慣例）。資料自部署起逐月累積，空清單顯示「尚無月營收資料」。此表獨立錯誤處理，載入失敗不影響上方 summary 區塊。

> 前端為每頁獨立 Vue app（[`frontend/components/StockQuery.vue`](frontend/components/StockQuery.vue)，進入點 [`frontend/src/query.js`](frontend/src/query.js)）；僅取數渲染，商業邏輯在後端。

## 功能：自選股

導覽列「自選股」（`/watchlist/`）唯讀呈現 `market.db` 的 watchlist/holdings（派工 D5）。

- **資料來源**：以 `WATCHLIST_USER_ID` 對應的 Discord 使用者為準，呼叫 `GET /api/watchlist/summary`。
- **自選股表**：代號、收盤、漲跌%（紅漲綠跌，台股慣例）、PE、PB、殖利率。
- **持股表**：代號、股數、均價、收盤、市值（`shares*close`）、未實現損益（`(close-avg_cost)*shares`）、報酬率（`(close-avg_cost)/avg_cost*100`；`avg_cost` 為 0/NULL 時顯示「—」）。
- **容錯**：個別代號缺行情以「—」呈現，不影響整包；watchlist 與 holdings 皆空時顯示提示。
- **唯讀**：本頁不提供任何編輯。**編輯請於 Discord `/watch` 或 Blazor 版操作**（依鐵律，本專案對 `market` 連線一律唯讀）。

> 整包回應以 Redis 快取（key `swd:v1:watchlist:{user_id}`，TTL 10 分鐘）。前端為獨立 Vue app（[`frontend/components/Watchlist.vue`](frontend/components/Watchlist.vue)，進入點 [`frontend/src/watchlist.js`](frontend/src/watchlist.js)）。

## 功能：法說會

導覽列「法說會」（`/conferences/`）唯讀呈現 `market.db` 的 `investor_conferences`（由 StockDCBot DC-K 入庫，派工 D6）。

- **資料來源**：呼叫 `GET /api/conferences/summary?days=30`（`days` 1~90，逾範圍回 `400 {"error": ...}`）。
- **即將召開**：`fact_date`（召開日）介於今日與今日+`days`（含）之公告，依召開日舊到新；欄位為召開日、代號、公司、主旨。
- **近期公告**：依發言日＋發言時間新到舊的近 20 筆，欄位為發言日、代號、公司、主旨。
- **容錯**：缺漏欄位顯示「—」；兩清單皆空時顯示提示。
- **資料性質**：為每日快照過濾入庫、自部署起累積，僅含主旨含「法人說明會」之公告；本頁唯讀（依鐵律，本專案對 `market` 連線一律唯讀）。

> 整包回應以 Redis 快取（key `swd:v1:conferences:{days}`，TTL 10 分鐘）。前端為獨立 Vue app（[`frontend/components/Conferences.vue`](frontend/components/Conferences.vue)，進入點 [`frontend/src/conferences.js`](frontend/src/conferences.js)）。

## 功能：行事曆

導覽列「行事曆」（`/calendar/`）以月曆檢視 `market.db` 的除權息（`dividend_events`）與法說會（`investor_conferences`）日期（派工 D7）。

- **資料來源**：呼叫 `GET /api/calendar/summary?month=YYYY-MM`（預設當月；格式不符或年份超出 2020~2099 回 `400 {"error": ...}`）。
- **月曆格線**：週一至週日七欄，純前端以該月資料組格；上／下月切換即重新呼叫 API，標題顯示「YYYY 年 M 月」，今日格高亮。
- **每日徽章**：除權息以紅色徽章（`event_type`＋代號，滑鼠停留顯示公司與配息/配股）；法說會以藍色徽章（「法說」＋代號，停留顯示公司與主旨）。
- **三態**：載入中／錯誤／無事件皆有明確提示。
- **資料性質**：除權息來自每交易日盤後入庫；法說會為每日快照過濾入庫、自部署起累積；本頁唯讀（依鐵律，本專案對 `market` 連線一律唯讀）。

> 整包回應以 Redis 快取（key `swd:v1:calendar:{month}`，TTL 10 分鐘）。前端為獨立 Vue app（[`frontend/components/Calendar.vue`](frontend/components/Calendar.vue)，進入點 [`frontend/src/calendar.js`](frontend/src/calendar.js)）。

## 功能：條件選股

導覽列「選股」（`/screener/`）以 `market.db` 最新交易日的行情（`daily_quotes`）＋估值（`valuation`）做複合條件篩選（派工 D8）。

- **資料來源**：呼叫 `GET /api/screener/results?<條件>`（下列條件皆選填，至少需帶一個，否則回 `400 {"error": "至少需指定一個篩選條件"}`；條件值非數值回 `400 {"error": ...}`）。
- **支援條件**：`pe_min`／`pe_max`、`pb_min`／`pb_max`、`yield_min`、`change_pct_min`／`change_pct_max`、`volume_lots_min`。
- **衍生欄**：漲跌%＝`change/(前收)*100`（前收＝`close-change`）；成交張數＝`volume/1000`。前收為 0 或來源缺值時該欄為 `null`；比對時該欄為 `null` 的列不符合（僅在有開該條件時排除）。
- **結果表**：代號、名稱、收盤、漲跌%（紅漲綠跌，台股慣例）、PE、PB、殖利率、成交張數；`null` 顯示「—」。依代號排序，顯示「符合 N 檔（顯示前 200）」，結果上限 200 筆。
- **三態**：載入中／錯誤／無符合皆有明確提示；前端於「全部留空」時擋下查詢。
- **資料性質**：僅為最新交易日單日快照的複合篩選（營收 YoY 與法人連買等進階條件留待後續）；本頁唯讀（依鐵律，本專案對 `market` 連線一律唯讀）。

> 基底資料（最新交易日全體行情＋估值）整包以 Redis 快取（key `swd:v1:screener:base:{date}`，TTL 10 分鐘）；篩選本身每請求即時計算不快取。前端為獨立 Vue app（[`frontend/components/Screener.vue`](frontend/components/Screener.vue)，進入點 [`frontend/src/screener.js`](frontend/src/screener.js)）。

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
