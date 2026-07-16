# StockWebDjango 開發待辦（派工 Prompt 集）

> 使用方式：每個區塊的 Prompt 為自包含內容，直接複製整段送給新的 Session 即可開工。
> 完成一區後在標題打勾並記錄 commit hash。規格依據：`docs/spec.md`（v0.1）。
> 執行順序：D0 → D1 → D2 → D3 → D4（D2/D3 理論可並行，保守串行）。
> 需要 StockDCBot 端配合的新資料源，一律回 StockDCBot repo 的 todolist.md 開 DC-x 派工。

---

## ☐ D0：專案骨架與環境（Django/DRF/Vite/Compose、雙庫與鐵律）

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支，目前僅有
docs/spec.md、todolist.md、AGENT.md）。請先完整閱讀 AGENT.md 與 docs/spec.md
並遵守其行為準則與鐵律；一律繁體中文。嚴禁提交任何 .env 檔（提供 .env.example）。

需求：依 spec §2/§3/§4/§8/§10/§11 建立可運行的專案骨架：
1. Django 5.2 LTS 專案：config/（settings 分層 base/dev/prod、urls、celery.py）、
   apps/core、apps/market、apps/dashboard、apps/stocks（後三個先空殼註冊）。
   依賴管理用 requirements.txt（或 uv/pip-tools 擇一並於 README 記載），每個
   依賴註明用途。
2. 雙資料庫與鐵律（spec §4）：default=PostgreSQL（DATABASE_URL）、
   market=SQLite 唯讀（MARKET_DB_PATH）。實作 Database Router（market app
   模型→market 庫、allow_migrate=False、寫入路由 None）＋唯讀連線
   （URI mode=ro 或 PRAGMA query_only，擇一實作）。apps/market 建
   managed=False 模型：market_daily、daily_quotes、valuation、
   monthly_revenue、quarterly_financials（欄位對照 StockDCBot storage.py
   的 CREATE TABLE，如無法讀取該 repo，以 docs/spec.md §4.3 的來源欄位
   與常識對映，並在回報中列出待核對欄位清單）。
3. Redis 快取（django-redis，REDIS_URL）與 Celery（broker/result=redis，
   config/celery.py＋core 一個 debug task）。
4. apps/core：GET /api/health（檢查 default DB、market DB、Redis 連通，
   全部 ok 回 200，任一失敗回 503 與明細）；DRF 全域設定（JSON only、
   anon throttle 60/min、統一 400 錯誤格式 {"error": "..."}）。
5. 前端建置鏈：frontend/（Vite＋Vue3.5＋Bootstrap 5.3＋lightweight-charts
   4.2.3，npm 依賴鎖版）；django-vite 整合；templates/base.html 引入建置
   產物（Navbar 佔位即可，D1 實作）。提供 npm run dev（HMR）與 build。
6. Docker Compose（spec §10）：nginx/web/worker/redis/postgres 五服務、
   healthcheck、market.db 以 MARKET_DB_PATH 環境變數注入並 :ro 掛載、
   Dockerfile 多階段（Node build → Python slim、非 root、collectstatic）、
   dev profile（僅 redis+postgres，宿主機 runserver 用）。
7. .env.example（MARKET_DB_PATH/DATABASE_URL/REDIS_URL/SECRET_KEY/
   ALLOWED_HOSTS，附註解）；.gitignore（python/node/.env/db volume）；
   ruff 設定；README（啟動步驟：compose 全套與 dev profile 兩種、測試指令）。
8. 測試（pytest＋pytest-django）：health 端點測試（Redis/market 以 fixture
   或 fakeredis／暫時 SQLite 檔）；「market 連線寫入必須失敗」的鐵律證明
   測試（spec §9）；router 路由測試。conftest 提供「暫時 SQLite market 庫」
   fixture（schema 僅建測試所需表，正式程式嚴禁 DDL）。

驗收：pytest 全綠；ruff check 無錯誤；docker compose config 可通過驗證
（環境無 Docker 時註明未實跑並列出啟動驗證步驟）；dev profile 下
runserver 可啟動且 /api/health 回應正確。完成後以 feat 前綴 commit
（訊息含「D0」，結尾加
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push。
回報：結構樹、依賴清單、鐵律測試說明、待核對欄位清單、測試數、hash。
```

## ☐ D1：外框 Navbar（首頁與其他功能）

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支）。
請先閱讀 AGENT.md 與 docs/spec.md（§6 前端規範）；一律繁體中文。
前置：D0 已完成（base.html 與 Vite 鏈可用）；不滿足請停止並回報。

需求：
1. templates/base.html 完成 Bootstrap 5.3 Navbar：品牌名「StockWeb」，
   連結自左至右＝「首頁」（/）、「查詢個股」（/stocks/query）；行動版
   收合（navbar-toggler）；當前頁高亮（active）。
2. 兩個頁面殼與路由：/（dashboard app，內容區先放置佔位卡片）、
   /stocks/query（stocks app，佔位表單）；皆繼承 base.html。
3. 共用版面：內容區 container、頁尾顯示資料來源說明（「資料由 StockDCBot
   於每交易日 17:00 後更新」）。
4. 測試：兩路由 200 與 template 使用斷言；Navbar active 邏輯測試。

驗收：pytest 全綠；ruff 無錯誤。完成後以 feat 前綴 commit（訊息含「D1」，
結尾加 Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push。
```

## ☐ D2：首頁儀表板（四圖卡，禁止拖動）

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支）。
請先閱讀 AGENT.md 與 docs/spec.md（§5/§6/§7）；一律繁體中文。
前置：D0/D1 已完成；market.db 需有 market_daily 資料（無資料請停止並回報）。

需求：
1. API：GET /api/dashboard/summary?days=60（days 1~252，預設 60；
   驗證錯誤回 400 {"error": ...}）。selectors 讀 market 庫 market_daily
   近 days 交易日（日期舊到新），services 組裝序列：
   - 三大法人近 20 日累積（foreign/trust/dealer 淨額，「股」換算「張」
     ÷1000，累積和序列）
   - 漲跌家數（up_count/down_count）與 A/D Line（up-down 累積）
   - 指數收盤與成交金額（金額以億元呈現）
   - 融資餘額趨勢（margin_balance）
   缺欄容錯：個別序列缺值以 null 帶出，不得使整包失敗。
2. Redis 快取整包回應（key swd:v1:dashboard:{days}，TTL 10 分鐘）。
3. 前端：Dashboard 頁 Vue app 呼叫 API，Bootstrap grid 排四張卡，圖表
   一律經共用 LwChart.vue（lightweight-charts 包裝）繪製；**鎖定互動：
   handleScroll:false、handleScale:false、fitContent() 固定範圍**（滑鼠
   拖動、滾輪縮放、觸控平移全部無效——此為明確驗收項）。載入中/錯誤/
   無資料三態 UI。
4. 測試：services 序列組裝（含缺欄容錯、張換算、累積計算）單元測試；
   API 參數驗證與快取行為（第二次呼叫不重查，可用 django cache 檢查）
   測試；以暫時 SQLite fixture 造 market_daily 假資料。

驗收：pytest 全綠；ruff 無錯誤。完成後以 feat 前綴 commit（訊息含「D2」，
結尾加 Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push。
```

## ☐ D3：個股快照資料層（stock_snapshots ＋ Celery 彙整）

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支）。
請先閱讀 AGENT.md 與 docs/spec.md（§4.3/§5/§7）；一律繁體中文。
前置：D0 已完成；market.db 需有 daily_quotes/valuation/monthly_revenue/
quarterly_financials 資料（缺表請停止並回報）。

需求（資料來源為 market.db 既有表的彙整，不解析原始 JSON——原始每日
JSON 不含財務指標，此為規格定案）：
1. apps/stocks 模型 StockSnapshot（default=PostgreSQL 庫，spec §4.3 欄位，
   unique(code, trade_date)，全欄位容錯 NULL）＋ migration。
2. services.build_snapshot(code)：自 market 庫彙整——
   - daily_quotes 最新兩日 → close、change_pct（(今收-昨收)/昨收*100）
   - valuation 最新日 → pe、pb、dividend_yield
   - monthly_revenue 最新月 → revenue_yoy、revenue_cum_yoy、revenue_month
   - quarterly_financials 最新季 → gross_margin＝毛利/營收*100、
     operating_margin＝營益/營收*100、eps、quarter（營收為 0/NULL 時
     比率為 NULL）
   個別來源缺漏容錯 NULL，不阻斷整體；查無此代號（daily_quotes 無列）
   回明確結果供 API 轉 400。
3. tasks.refresh_snapshot(code)：Celery task——呼叫 build_snapshot、
   upsert StockSnapshot（同 code+trade_date 冪等）、失效 Redis
   swd:v1:stock:{code}；Redis lock 防同代號併發、失敗可重試
   max_retries=3、成功失敗皆留 log。
4. API：GET /api/stocks/{code}/summary（code 驗證 4-6 位英數）——
   - 快照存在且 trade_date == market 庫 daily_quotes 最新交易日 →
     200 回最新指標＋近 20 個交易日快照列表（新到舊）
   - 否則 enqueue refresh_snapshot 並回 202 {"status": "processing"}
   - 查無代號 → 400
   回應以 Redis 快取（TTL 10 分鐘，task 寫入後主動失效）。
5. 測試：build_snapshot 各來源齊全/缺漏/代號不存在/營收為 0 的單元測試
   （暫時 SQLite fixture）；task 冪等與快取失效測試（CELERY_TASK_ALWAYS_EAGER）；
   API 200/202/400 三分支測試。

驗收：pytest 全綠；ruff 無錯誤。完成後以 feat 前綴 commit（訊息含「D3」，
結尾加 Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push。
回報：欄位對映結果（與 StockDCBot storage.py 的核對情形）、測試數、hash。
```

## ☐ D4：查詢個股資訊頁

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支）。
請先閱讀 AGENT.md 與 docs/spec.md（§5/§6/§7）；一律繁體中文。
前置：D1/D3 已完成；不滿足請停止並回報。

需求：
1. /stocks/query 頁 Vue app：代號輸入框（前端先驗 4-6 位英數）＋查詢
   按鈕；呼叫 GET /api/stocks/{code}/summary。
2. 202 processing 時顯示「彙整中…」並以 1 秒間隔輪詢（上限 10 次，
   超過顯示逾時錯誤與重試按鈕）；400 顯示 API 錯誤訊息。
3. 200 時呈現：
   - 指標卡列（Bootstrap cards）：收盤與漲跌%（紅漲綠跌，台股慣例）、
     本益比、股價淨值比、殖利率、月營收 YoY、累計營收 YoY、毛利率、
     營業利益率、EPS——每卡標註資料基準（trade_date／revenue_month／
     quarter），NULL 顯示「—」
   - 近期資料表：近 20 個交易日快照（日期、收盤、漲跌%、PE、PB、
     殖利率），Bootstrap table
4. 測試：頁面路由測試；（前端邏輯屬 Vue，行為以 API 測試保障，前端
   不做單元測試——與 spec §9 一致）。

驗收：pytest 全綠；ruff 無錯誤；README 補「查詢個股」使用說明。完成後
以 feat 前綴 commit（訊息含「D4」，結尾加
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push。
```

---

## 已完成（記錄用）

（尚無）
