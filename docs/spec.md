# StockWebDjango 系統規格書 v0.1

> 台股盤後研究網頁的 Django 重寫版。與 StockDCBot（資料擷取）、StockWeb（.NET Blazor 版，並行存在）為姊妹專案。
> 本文件為企業規格：先確立決策、邊界與各層規範，開發依 `todolist.md` 派工 Prompt 逐區執行。
> 文件維護原則：任何絕對路徑一律不寫入本文件與派工 Prompt（雙機開發，路徑由 `.env` 與 AGENT.md 承載）。

---

## 1. 定位與範圍

**定位**：單人使用的「盤後」研究工具。資料每交易日 17:00 後由 StockDCBot 寫入 SQLite `market.db`；本系統負責查詢、彙整與視覺化。不做即時報價、不做下單、不做推播。

**第一版範圍（對應 todolist 派工 D1-D4）**：

| # | 功能 | 摘要 |
|---|---|---|
| D1 | 外框與導覽 | Bootstrap Navbar，自左至右：首頁、其他功能 |
| D2 | 首頁儀表板 | 四張圖卡：三大法人近 20 日累積（張）、漲跌家數與 A/D Line、指數與成交金額、融資餘額趨勢；圖表**禁止使用者拖動/縮放** |
| D3 | 個股快照資料層 | Django 自有 `stock_snapshots` 表：查詢觸發自 market.db 既有表彙整（漲跌、PE、PB、殖利率、月營收 YoY、累計營收 YoY、毛利率、營業利益率、EPS），Celery 非同步寫入＋Redis 快取 |
| D4 | 個股查詢頁 | 輸入代號 → 顯示 D3 的近期各項資料 |

**明確不做（第一版）**：條件選股、自選股、行事曆、新聞法說會、使用者帳號系統、market.db 遷移。

**第二版範圍（2026-07-17 定案，07-18 增補 D6/D7）**：D5 自選股與持股頁——唯讀
呈現 market.db 的 watchlist/holdings（編輯入口維持在 Discord /watch 與 Blazor 版），
逐檔附最新行情/估值與持股損益計算。D6 法說會資訊頁——唯讀呈現
investor_conferences（DC-K 入庫）：即將召開清單與近期公告。D7 行事曆頁——
月曆檢視除權息（dividend_events）與法說會（investor_conferences）日期。
D8 條件選股頁——以最新交易日的行情＋估值做複合條件篩選（PE/PB/殖利率/
漲跌%/成交張數；營收 YoY 與法人連買等進階條件留待後續）。
D9 查詢個股月營收對比表——查詢個股頁新增表格，列出該代號於 monthly_revenue
的「全部」月份（營收、月增率、年增率、累計營收、累計年增率；資料自部署起
逐月累積）。其餘（帳號系統）仍不做。

**第三版範圍（2026-07-20 定案）**：D10 個股 K 線圖——查詢個股頁新增
Lightweight Charts K 線（daily_quotes 近 252 日、還原/未還原切換、成交量與
三大法人買賣超副圖）；前復權邏輯移植 StockDCBot `analysis.adjust_history`
（**公式與測試數字以 Bot 端為權威對齊**；market app 需補 dividend_events、
institutional 兩個 managed=False 模型）。D11 產業同業比較——查詢個股頁新增
「同業比較」區塊：以 company_profile（DC-M 入庫）取得同產業個股，對比最新
PE/PB/殖利率/月營收 YoY/毛利率（本股高亮；company_profile 表不存在或產業
無同業時容錯顯示原因）。D12 儀表板近期警示卡——讀 StockDCBot
`reports/YYYY-MM/*.json` 的 `sections.market_alerts` 彙整最近警示（新增
`REPORTS_DIR` 環境變數，compose 以 `:ro` 掛載報告目錄——純 JSON 檔案讀取，
無 WAL 問題；目錄不存在/缺檔容錯）。帳號系統仍不做。

---

## 2. 技術選型（決策記錄）

| 層 | 選擇 | 版本基準 | 決策理由 |
|---|---|---|---|
| 語言/框架 | Python + Django | Python 3.12、Django 5.2 LTS | 與 StockDCBot 同語言，還原價等純邏輯未來可共用；LTS 支援期長 |
| API | Django REST Framework | 3.15+ | 企業慣例；序列化/驗證/瀏覽器可測 |
| 前端骨架 | Bootstrap | 5.3 | 使用者指定 |
| 前端資料流 | Vue 3 | 3.5（Composition API） | 使用者指定；每頁掛載獨立 Vue app（MPA 模式，Django template 出殼、Vue 負責取數與渲染），不做整站 SPA |
| 前端建置 | Vite ＋ django-vite | Node 22 LTS | SFC 與依賴管理正規化；容器多階段建置產出靜態資源交 Nginx |
| 圖表 | TradingView Lightweight Charts | 4.2.3（與 StockWeb 對齊） | 使用者指定；以 Vue 元件包裝，全站唯一圖表入口 |
| 快取 | Redis（django-redis） | Redis 7 | 使用者指定 |
| 非同步 | Celery（Redis broker/result） | 5.4 | 使用者指定 |
| 自有資料庫 | PostgreSQL | 16 | 見 §4 雙庫決策 |
| 市場資料庫 | SQLite `market.db`（唯讀掛載） | — | 契約沿用：Bot 寫、Web 讀 |
| WSGI/入口 | Gunicorn ＋ Nginx | Gunicorn 23 | 使用者指定；Nginx 供靜態資源與反向代理 |
| 容器化 | Docker Compose | Compose v2 | 使用者指定「未來可容器化」→ 第一版即以 Compose 為唯一部署形態（開發亦可容器內跑） |
| 測試 | pytest ＋ pytest-django | 8.x | 企業慣例；fixture 建暫時 SQLite/使用測試 PostgreSQL |

---

## 3. 系統架構

### 3.1 容器拓撲（Docker Compose）

```
                        ┌──────────────────────── docker compose ────────────────────────┐
瀏覽器 ── :80 ──► nginx ─┤ /static/*  直接回應（Vite 建置產物、Bootstrap、charts）        │
                        │ 其餘      ──► web（Gunicorn + Django/DRF）                     │
                        │                    │            │                              │
                        │                    │            ├─► postgres（Django 自有資料）│
                        │                    │            ├─► redis（快取）              │
                        │                    │            └─► market.db（唯讀 volume）   │
                        │ worker（Celery）───┴─ 同上三個資料來源；broker/result = redis  │
                        └────────────────────────────────────────────────────────────────┘
```

- `market.db` 以**所在目錄 bind mount（可寫）** 掛入 web 與 worker 容器（`MARKET_DB_DIR` → `/data`），實體檔案在宿主機由 StockDCBot 維護。SQLite WAL 模式（Bot 端開啟）讀取需在同目錄建立 `-wal`/`-shm` 輔助檔，檔案系統層 `:ro` 與 WAL 先天不相容；唯讀保證在連線層（`PRAGMA query_only`＋Database Router 雙保險，見 §4.2），非檔案系統層。
- 服務皆定義 healthcheck；web/worker 以 `depends_on: condition: service_healthy` 排序啟動。

### 3.2 應用分層（Django 專案內）

```
config/                     # settings 分層（base / dev / prod）、urls、celery app
apps/
  core/                     # 共用：例外、回應格式、分頁、健康檢查端點
  market/                   # market.db 唯讀存取層：managed=False 模型 + selectors（唯讀查詢函數）
  dashboard/                # D2：儀表板 API 與頁面
  stocks/                   # D3+D4：stock_snapshots 模型、彙整 services、Celery tasks、查詢 API 與頁面
frontend/                   # Vite 工作區：Vue3 SFC、chart 包裝元件、Bootstrap 匯入
templates/                  # Django templates：base.html（Navbar）＋各頁殼
```

分層規約（對齊姊妹專案的「純邏輯可測試」原則）：
- **selectors.py**：唯讀查詢（進 DB、出 dataclass/dict），不含商業邏輯。
- **services.py**：純商業邏輯（彙整、比率計算、序列組裝），不碰 HTTP；單元測試主要對象。
- **views/serializers**：薄層——驗證輸入、呼叫 service/selector、序列化輸出。
- Vue 只負責「取 API 資料 → 渲染」，不含商業邏輯；圖表一律經共用 chart 元件。

---

## 4. 資料架構與鐵律

### 4.1 雙資料庫決策

| 庫 | 引擎 | 角色 | 寫入權 |
|---|---|---|---|
| `market`（market.db） | SQLite（唯讀） | StockDCBot 產出的市場資料：daily_quotes、valuation、monthly_revenue、quarterly_financials、market_daily、institutional、margin、dividend_events… | **本系統禁止任何寫入與 DDL** |
| `default`（PostgreSQL） | PostgreSQL 16 | Django 自有資料：`stock_snapshots`、django 系統表（sessions 等） | 本系統獨占 |

> 決策說明：market.db 的 schema 歸 StockDCBot `storage.py` 獨占管理（兩專案既有契約），Django 的新表不得建入；Gunicorn 多 worker＋Celery 多進程的並發寫入也不適合 SQLite。故 Django 自有資料落 PostgreSQL，market.db 維持唯讀資料源。未來 market.db 若遷移 PostgreSQL，只需改 `market` 連線設定，應用層不動。

### 4.2 鐵律（違反即為錯誤，繼承兩專案契約）

1. `market.db` schema 歸 StockDCBot 管理：本系統嚴禁對 `market` 連線 CREATE/ALTER/DROP/INSERT/UPDATE/DELETE。需要新市場資料時，回 StockDCBot 開 DC-x 派工。
2. `market` 連線以唯讀方式開啟（SQLite URI `mode=ro` 或 connection signal 執行 `PRAGMA query_only=ON`，實作擇一並以測試證明寫入會失敗），並以 **Database Router** 雙保險：`market` app 模型 `managed=False`、routed 至 `market` 庫、`allow_migrate=False`、寫入路由回 `None`。
3. 機密與路徑一律走環境變數（`.env`，嚴禁提交；提供 `.env.example`）：`MARKET_DB_PATH`、`DATABASE_URL`、`REDIS_URL`、`SECRET_KEY`、`ALLOWED_HOSTS`。
4. 測試中建表僅限測試用暫時 SQLite 檔與測試 PostgreSQL，不在此限。

### 4.3 stock_snapshots（Django 自有，PostgreSQL）

一檔股票每交易日一列（`unique_together: code + trade_date`），欄位全部允許 NULL（來源缺漏容錯）：

| 欄位 | 型別 | 來源（market.db） |
|---|---|---|
| code / name / market | text | daily_quotes（name）、valuation |
| trade_date | date | daily_quotes 最新日 |
| close / change_pct | numeric | daily_quotes 最新兩日計算 |
| pe / pb / dividend_yield | numeric | valuation 最新日 |
| revenue_yoy / revenue_cum_yoy / revenue_month | numeric / text | monthly_revenue 最新月 |
| gross_margin / operating_margin / eps / quarter | numeric / text | quarterly_financials 最新季（毛利率＝毛利/營收、營益率＝營益/營收，讀取端計算） |
| updated_at | timestamptz | 寫入時間 |

---

## 5. API 規格（DRF，全部回 JSON）

| 端點 | 說明 | 資料來源 |
|---|---|---|
| `GET /api/health` | 健康檢查（DB/Redis 連通性），供容器 healthcheck | — |
| `GET /api/dashboard/summary?days=60` | 市場序列：日期、指數、成交金額、漲跌家數、三大法人淨額（張）、融資餘額；`days` 上限 252 | market_daily（Redis 快取） |
| `GET /api/stocks/{code}/summary` | 個股近期各項資料（D3 快照，近 N 日列表＋最新指標卡） | stock_snapshots（Redis 快取） |
| `GET /api/stocks/{code}/quotes?days=252&adjusted=true` | 個股日 K（OHLCV＋三大法人淨額；`adjusted` 前復權） | daily_quotes＋dividend_events＋institutional（Redis 快取） |
| `GET /api/stocks/{code}/peers` | 同產業個股對比（估值/營收 YoY/毛利率） | company_profile＋valuation＋monthly_revenue＋quarterly_financials（Redis 快取） |
| `GET /api/dashboard/alerts?days=5` | 最近 N 個交易日市場警示 | StockDCBot reports JSON（`REPORTS_DIR`，Redis 快取） |

規約：
- 輸入驗證：`code` 為 4-6 位英數、`days` 1~252、日期須合法；錯誤一律 `400 {"error": "<訊息>"}`，不回 500。
- 回應欄位 snake_case；數值缺漏回 `null`，由前端顯示「—」。
- 快照尚未就緒時 `GET /api/stocks/{code}/summary` 回 `202 {"status": "processing"}`，前端輪詢（見 §7）。

---

## 6. 前端規範

- **版面**：Bootstrap 5.3，`templates/base.html` 定義 Navbar（自左至右：首頁、查詢個股；後續功能依序右接）與內容容器；RWD 由 Bootstrap grid 承擔。
- **資料流**：每頁一個 Vue3 app（Composition API），以 `fetch` 呼叫 §5 API；載入中/錯誤/空資料三態都要有明確 UI。禁止在 template 內嵌大量 inline JS。
- **圖表**：Lightweight Charts 統一由 `frontend/components/LwChart.vue` 包裝（props 進資料、事件不外漏），全站不得另建圖表入口。儀表板圖表一律鎖定互動：`handleScroll: false`、`handleScale: false`（滑鼠拖動、滾輪縮放、觸控全關），資料範圍以 `fitContent()` 固定。
- **建置**：Vite 產出帶 hash 的靜態資源；Django 端以 django-vite 注入。開發模式支援 HMR；正式建置產物由 Nginx 服務。

---

## 7. 快取與非同步規範

- **Redis 快取**（django-redis，key 一律加版本前綴 `swd:v1:`）：
  - 儀表板序列：key `swd:v1:dashboard:{days}`，TTL 10 分鐘（盤後資料日更，10 分鐘足夠）。
  - 個股快照回應：key `swd:v1:stock:{code}`，TTL 10 分鐘；Celery 寫入新快照後主動失效。
- **Celery**（queue 預設一條；task 冪等、可重試 `max_retries=3`）：
  - `stocks.tasks.refresh_snapshot(code)`：自 market.db 彙整 → upsert `stock_snapshots` → 失效 Redis。同一代號以 Redis lock 防併發重算。
  - 查詢流程：API 收到查詢 → 快照存在且 `trade_date` 等於 market.db 最新交易日 → 直接回；否則 enqueue task 並回 202，前端以 1 秒間隔輪詢（上限 10 次後顯示錯誤）。
- Celery beat 第一版不啟用（快照採查詢觸發）；預留設定位。

---

## 8. 組態、日誌與安全

- settings 分層：`config/settings/base.py`＋`dev.py`＋`prod.py`；一切差異走環境變數（django-environ）。
- 日誌：structured logging（JSON formatter 於 prod），等級 INFO；Celery task 成功/失敗必留紀錄。Gunicorn access log 開啟。
- 安全基線：`DEBUG=False`（prod）、`SECRET_KEY` 唯環境變數、`ALLOWED_HOSTS` 明列、DRF throttle（anon 60/min）、Nginx 加基本 security headers。本系統單人內網使用，第一版不做帳號系統，但所有寫入型端點（目前無）預設關閉。

---

## 9. 測試策略

- pytest＋pytest-django；測試資料庫：PostgreSQL 用 pytest-django 自建、market.db 用 **fixture 產生暫時 SQLite 檔**（schema 抄 StockDCBot `storage.py` 必要表，僅測試用）。
- 覆蓋要求：services/selectors 全覆蓋；views 以 API 測試覆蓋主要路徑與 400/202 分支；Celery task 以 eager mode 測試。
- 鐵律測試：對 `market` 連線嘗試寫入必須失敗（§4.2 的證明測試）。
- 全部測試綠才可 commit（工作流與姊妹專案一致）。

---

## 10. 部署（Compose）

- `compose.yaml` 服務：`nginx`、`web`（Gunicorn：`--workers 2 --threads 2`、`--timeout 60`）、`worker`（celery worker，concurrency 2）、`redis`、`postgres`（volume 持久化）；`market.db` 由宿主機目錄以環境變數（`MARKET_DB_DIR`）注入、掛載目錄且可寫（WAL 需建 `-wal`/`-shm` 輔助檔；唯讀保證在連線層，見 §3.1/§4.2）。
- Dockerfile 多階段：stage1 Node 22 跑 Vite build → stage2 Python 3.12-slim 裝依賴、collectstatic、以非 root user 執行 Gunicorn。
- `docker compose up` 一鍵啟動即為驗收環境；開發亦可宿主機 `runserver`＋容器內 redis/postgres（compose 提供 `dev` profile）。

---

## 11. 編碼規範

- Python：ruff（lint＋format）、型別註記（公開函數必註）、docstring 繁中。
- 前端：Vue SFC `<script setup>`、ESLint＋Prettier 預設。
- 命名：Django app 內 `models / selectors / services / serializers / views / tasks / urls` 檔案職責固定（見 §3.2）。
- Git：`feat:`/`fix:`/`chore:`/`docs:` 前綴＋繁中摘要；測試全綠才 commit；不 push（由管理流程統一）。
- 回覆與文件一律繁體中文。

---

## 12. 版本規劃與派工對照

| 派工 | 內容 | 前置 |
|---|---|---|
| D0 | 專案骨架：Django/DRF/Vite/Compose 全套環境、雙庫與鐵律、健康檢查 | 無 |
| D1 | 外框 Navbar（首頁、查詢個股） | D0 |
| D2 | 首頁儀表板四圖卡（禁拖動） | D0、D1 |
| D3 | stock_snapshots 資料層＋Celery 彙整 | D0 |
| D4 | 個股查詢頁 | D1、D3 |
| D5 | 自選股與持股頁（唯讀呈現 watchlist/holdings＋損益計算） | D1、D2（LwChart 非必要，僅沿用版面慣例） |
| D6 | 法說會資訊頁（唯讀呈現 investor_conferences：即將召開＋近期公告） | D1 |
| D7 | 行事曆頁（月曆檢視 dividend_events＋investor_conferences 日期） | D1、D6 |
| D8 | 條件選股頁（最新交易日行情＋估值複合篩選） | D1 |
| D9 | 查詢個股月營收對比表（monthly_revenue 全月份） | D3、D4 |

派工 Prompt 全文見 `todolist.md`。執行順序：D0 → D1 → (D2 ∥ D3) → D4；D2 與 D3 無共用檔案時可並行，保守起見仍建議串行。
