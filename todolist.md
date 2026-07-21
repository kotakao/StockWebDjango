# StockWebDjango 開發待辦（派工 Prompt 集）

> 使用方式：每個區塊的 Prompt 為自包含內容，直接複製整段送給新的 Session 即可開工。
> 完成一區後在標題打勾並記錄 commit hash。規格依據：`docs/spec.md`（v0.1）。
> 執行順序：第一版 D0→D4、第二版 D5→D9（皆已完成）；第三版 D10 → D11 → D12
>（D11/D12 互不相依可換序，與 D10 共用查詢頁/儀表板檔案，一律串行）。
> 需要 StockDCBot 端配合的新資料源，一律回 StockDCBot repo 的 todolist.md 開 DC-x 派工。

---

## ☑ D0：專案骨架與環境（Django/DRF/Vite/Compose、雙庫與鐵律）— commit `7e76301`

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

## ☑ D1：外框 Navbar（首頁與其他功能）— commit `eaf9c7e`

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

## ☑ D2：首頁儀表板（四圖卡，禁止拖動）— commit `2d5f4fe`

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

## ☑ D3：個股快照資料層（stock_snapshots ＋ Celery 彙整）— commit `24a6791`

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

## ☑ D4：查詢個股資訊頁 — commit `df886f3`

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

# 第二版派工

## ☑ D5：自選股與持股頁（唯讀呈現）— commit `bea91cf`

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支）。
請先閱讀 AGENT.md 與 docs/spec.md（§4 鐵律、§5/§6/§7）；一律繁體中文。
嚴禁提交任何 .env 檔。工作區若有使用者未提交的變更勿動勿納入。
前置：D1-D4 已完成；market.db 需有 watchlist 資料（無資料仍可開發，
以測試 fixture 為準）。本機無 Node.js：前端只寫程式碼不 build，
行為以 API 測試保障（與 spec §9 一致）。

背景：market.db 的 watchlist（user_id TEXT + code，主鍵複合）與
holdings（user_id TEXT + code、shares REAL、avg_cost REAL、updated_at TEXT，
主鍵複合）由姊妹專案維護（Discord /watch 指令與 Blazor 版寫入）。
本專案依鐵律對 market 連線「一律唯讀」——本功能只呈現、不提供任何
編輯；編輯入口在 Discord 與 Blazor 版，頁面上須註明此事。

需求：
1. 設定：WATCHLIST_USER_ID 環境變數（預設 "0"，.env.example 補註解
   「Discord 使用者 ID，對應 market.db watchlist/holdings 的 user_id」）。
2. apps/market 補 managed=False 模型：watchlist、holdings（欄位如上，
   複合主鍵以 Meta unique_together 或 composite pk 慣例處理，維持唯讀）。
3. API：GET /api/watchlist/summary——selectors 讀 market 庫：
   - 該 user_id 的 watchlist 代號清單，逐檔附最新 daily_quotes
     （close、change_pct 以最新兩日計算）與最新 valuation（pe、pb、
     dividend_yield）
   - 該 user_id 的 holdings 逐檔附最新收盤，services 計算：市值
     （shares*close）、未實現損益（(close-avg_cost)*shares）、報酬率
     （(close-avg_cost)/avg_cost*100，avg_cost 為 0/NULL 時為 NULL）
   - 個別代號缺行情容錯 null，不得使整包失敗；watchlist 與 holdings
     皆空時回空清單（200）
   整包 Redis 快取（key swd:v1:watchlist:{user_id}，TTL 10 分鐘）。
4. 前端：Navbar 新增「自選股」（/watchlist，dashboard/stocks 之後，
   active 高亮比照既有）；頁面 Vue app 兩區塊 Bootstrap table：
   自選股（代號、收盤、漲跌%、PE、PB、殖利率）與持股（代號、股數、
   均價、收盤、市值、未實現損益、報酬率），紅漲綠跌台股慣例、
   NULL 顯示「—」；載入中/錯誤/空清單三態；頁尾註明「編輯請於
   Discord /watch 或 Blazor 版操作」。
5. 測試：selectors/services 單元測試（暫時 SQLite fixture 補建
   watchlist/holdings 表——僅測試 DDL，正式程式嚴禁 DDL）；損益計算
   （含 avg_cost 0/NULL、缺行情）測試；API 快取行為與空清單測試；
   頁面路由測試。
6. 鐵律不變：不動 config/routers.py 與唯讀機制；不新增資料表
   （PostgreSQL 端本功能無自有資料）。

驗收：pytest 全綠（既有 42 只增不減）；ruff 無錯誤；README 補
「自選股」使用說明與 WATCHLIST_USER_ID 設定說明。完成後以 feat 前綴
commit（訊息含「D5」，結尾加
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push、
不要動 todolist.md（由管理流程更新）。
回報：改動清單、測試數、hash。
```

## ☑ D6：法說會資訊頁（唯讀呈現）— commit `2d6a3c6`＋fix `b50981c`

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支）。
請先閱讀 AGENT.md 與 docs/spec.md（§4 鐵律、§5/§6/§7）；一律繁體中文。
嚴禁提交任何 .env 檔。工作區若有使用者未提交的變更勿動勿納入。
前置：D1-D5 已完成；本機無 Node.js：前端只寫程式碼不 build，
行為以 API 測試保障（與 spec §9 一致）。

背景：market.db 的 investor_conferences 表（StockDCBot DC-K 入庫）——
主鍵 market+code+announce_date+announce_time，欄位另有 name、subject、
matched_clause、fact_date（法說會召開日）、description、report_date，
日期皆 ISO YYYY-MM-DD、時間 HH:MM:SS，缺漏容錯 NULL。此為每日快照
過濾入庫（主旨含「法人說明會」），自部署起累積。本專案依鐵律對
market 連線一律唯讀。

需求：
1. apps/market 補 managed=False 模型 InvestorConference（複合主鍵
   比照既有慣例）與 selectors：
   - upcoming_conferences(days)：fact_date 介於今日與今日+days（含），
     依 fact_date 舊到新
   - recent_conference_announcements(limit=20)：依 announce_date+
     announce_time 新到舊
2. API：GET /api/conferences/summary?days=30（days 1~90，驗證錯誤回
   400 {"error": ...}）——回 {"days": n, "upcoming": [...], "recent": [...]}，
   每筆含 market、code、name、subject、fact_date、announce_date；
   兩清單皆空回空清單（200）。整包 Redis 快取
   （key swd:v1:conferences:{days}，前綴比照既有由 CACHES 加上，
   TTL 10 分鐘）。
3. 前端：Navbar 新增「法說會」（/conferences，「自選股」之後，active
   高亮比照既有）；頁面 Vue app 兩區塊 Bootstrap table：即將召開
   （召開日、代號、公司、主旨）與近期公告（發言日、代號、公司、主旨），
   NULL 顯示「—」；載入中/錯誤/空清單三態；頁尾註明資料性質
   （每日快照自部署起累積、僅含主旨含「法人說明會」之公告）。
   vite 進入點比照既有頁面。
4. 鐵律不變：不動 config/routers.py 與唯讀機制；不新增資料表；
   對 market 連線嚴禁任何寫入。
5. 測試：selectors 日期窗（含邊界日、fact_date NULL 不入 upcoming）
   單元測試（暫時 SQLite fixture 補建 investor_conferences 表——僅測試
   DDL）；API 參數驗證（days 0/91 → 400）、快取行為、空清單測試；
   頁面路由與 Navbar active 測試。

驗收：pytest 全綠（既有 55 只增不減）；ruff 無錯誤；README 補
「法說會」使用說明。完成後以 feat 前綴 commit（訊息含「D6」，結尾加
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push、
不要動 todolist.md（由管理流程更新）。
回報：改動清單（檔案與重點）、新增測試說明、測試總數、commit hash。
```

## ☑ D7：行事曆頁（月曆檢視除權息與法說會）— commit `1eaca6e`

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支）。
請先閱讀 AGENT.md 與 docs/spec.md（§4 鐵律、§5/§6/§7）；一律繁體中文。
嚴禁提交任何 .env 檔。工作區若有使用者未提交的變更勿動勿納入。
前置：D1-D6 已完成；本機無 Node.js：前端只寫程式碼不 build，
行為以 API 測試保障（與 spec §9 一致）。

背景：market.db 兩個日期事件來源（本專案依鐵律對 market 連線一律唯讀）：
- dividend_events（StockDCBot 功能區 I 入庫）——主鍵 market+code+ex_date，
  欄位另有 name、event_type、cash_dividend（REAL）、stock_ratio（REAL），
  ex_date 為 ISO YYYY-MM-DD，缺漏容錯 NULL。
- investor_conferences——D6 已建 managed=False 模型與 selectors，
  fact_date 為法說會召開日。

需求：
1. apps/market 補 managed=False 模型 DividendEvent（複合主鍵比照既有
   慣例）與 selectors：
   - dividend_events_between(start, end)：ex_date 介於 start 與 end
     （含），依 ex_date、market、code 排序
   - conference_dates_between(start, end)：fact_date 同上區間，依
     fact_date、market、code 排序（可沿用/擴充 D6 selectors，擇簡）
2. API：GET /api/calendar/summary?month=YYYY-MM（預設當月；格式不符或
   年份超出 2020~2099 回 400 {"error": ...}）——回
   {"month": "YYYY-MM", "dividends": [...], "conferences": [...]}：
   dividends 每筆含 market、code、name、event_type、ex_date、
   cash_dividend、stock_ratio；conferences 每筆含 market、code、name、
   subject、fact_date。皆空回空清單（200）。整包 Redis 快取
   （key swd:v1:calendar:{month}，前綴比照既有由 CACHES 加上，TTL 10 分鐘）。
3. 前端：Navbar 新增「行事曆」（/calendar，「法說會」之後，active 高亮
   比照既有）；頁面 Vue app 月曆格線（週一至週日七欄，純前端以
   month 資料組格）：
   - 上／下月切換按鈕與當月標題（YYYY 年 M 月），切換即重新呼叫 API
   - 每日格內以小徽章列出事件：除權息（event_type＋代號，滑鼠 title
     顯示名稱與配息/配股數）與法說會（「法說」＋代號，title 顯示公司
     與主旨）；今日格高亮
   - 載入中/錯誤/無事件三態；頁尾註明資料性質（法說會為每日快照自
     部署起累積）
   vite 進入點比照既有頁面。月曆組格為前端邏輯，不做前端單元測試
   （spec §9），後端以 API 測試保障。
4. 鐵律不變：不動 config/routers.py 與唯讀機制；不新增資料表；
   對 market 連線嚴禁任何寫入。
5. 測試：selectors 日期窗（含月初月底邊界、跨月不入列）單元測試
   （fixture 補建 dividend_events 表——僅測試 DDL）；API month 驗證
   （格式錯誤/2019-12/2100-01 → 400、預設當月、邊界 2020-01/2099-12
   → 200）、快取行為、空清單測試；頁面路由與 Navbar active 測試。

驗收：pytest 全綠（既有 73 只增不減）；ruff 無錯誤；README 補
「行事曆」使用說明。完成後以 feat 前綴 commit（訊息含「D7」，結尾加
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push、
不要動 todolist.md（由管理流程更新）。
回報：改動清單（檔案與重點）、新增測試說明、測試總數、commit hash。
```

## ☑ D8：條件選股頁（最新交易日行情＋估值複合篩選）— commit `89b7b07`

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支）。
請先閱讀 AGENT.md 與 docs/spec.md（§4 鐵律、§5/§6/§7）；一律繁體中文。
嚴禁提交任何 .env 檔。工作區若有使用者未提交的變更勿動勿納入。
前置：D1-D7 已完成；本機無 Node.js：前端只寫程式碼不 build，
行為以 API 測試保障（與 spec §9 一致）。

背景：market.db 的 daily_quotes（主鍵 market+date+code，欄位 name、
open/high/low/close、change【漲跌絕對值，非百分比】、volume【成交股數】）
與 valuation（主鍵 market+date+code，欄位 pe、dividend_yield、pb）皆有
managed=False 模型可沿用（apps/market/models.py）。本專案依鐵律對
market 連線一律唯讀。個股數約兩千檔，單日資料量小。

需求：
1. selectors 補：latest_quote_date()（daily_quotes 最大 date）與
   quotes_with_valuation(date)：該日全部 daily_quotes 列 LEFT JOIN 同日
   valuation（以 market+code 對齊；valuation 缺列時 pe/pb/dividend_yield
   為 None）。可用兩次查詢在 Python 端以 dict 合併，擇簡。
2. services 純函數 screen(rows, filters)：
   - 衍生欄 change_pct＝change/(close-change)*100（前收＝close-change；
     前收為 0/None 或 close/change 缺值時 change_pct 為 None）、
     volume_lots＝volume/1000（張，volume None 時 None）
   - 支援條件（全部選填）：pe_min/pe_max、pb_min/pb_max、yield_min、
     change_pct_min/change_pct_max、volume_lots_min
   - 條件比對時該欄為 None 的列一律不符合（有開該條件才排除）
   - 回傳依 code 排序，上限 200 筆並附總符合數
3. API：GET /api/screener/results?（上述條件為 query 參數）——
   - 至少需帶一個條件，否則 400 {"error": "至少需指定一個篩選條件"}；
     參數非數值回 400 {"error": ...}
   - 回 {"date": 最新交易日, "total": 總符合數, "results": [...]}，每筆含
     market、code、name、close、change_pct、pe、pb、dividend_yield、
     volume_lots（數值容錯 null）
   - 基底資料快取：quotes_with_valuation 結果以
     key swd:v1:screener:base:{date}（前綴比照既有由 CACHES 加上，
     TTL 10 分鐘）整包快取，篩選本身每請求即時計算不快取
   - daily_quotes 無任何資料時回 200 {"date": null, "total": 0,
     "results": []}
4. 前端：Navbar 新增「選股」（/screener，「行事曆」之後，active 高亮
   比照既有）；頁面 Vue app：條件表單（PE 上/下限、PB 上/下限、
   殖利率下限、漲跌% 上/下限、成交張數下限，皆數字輸入可留空）＋
   查詢按鈕（前端擋「全部留空」）；結果 Bootstrap table（代號、名稱、
   收盤、漲跌%、PE、PB、殖利率、成交張數），漲跌% 紅漲綠跌、NULL 顯示
   「—」；顯示「符合 N 檔（顯示前 200）」；載入中/錯誤/無符合三態。
   vite 進入點比照既有頁面。
5. 鐵律不變：不動 config/routers.py 與唯讀機制；不新增資料表；
   對 market 連線嚴禁任何寫入。
6. 測試：services screen 單元測試（各條件獨立與複合、change_pct 計算
   含前收 0/缺值容錯、None 欄位在開條件時被排除、上限 200 與 total）；
   selectors join 測試（valuation 缺列容錯）；API 驗證（無條件 400、
   非數值 400）、快取行為（基底快取第二次不重查）、無資料 200 測試；
   頁面路由與 Navbar active 測試。

驗收：pytest 全綠（既有 93 只增不減）；ruff 無錯誤；README 補
「條件選股」使用說明。完成後以 feat 前綴 commit（訊息含「D8」，結尾加
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push、
不要動 todolist.md（由管理流程更新）。
回報：改動清單（檔案與重點）、新增測試說明、測試總數、commit hash。
```

## ☑ D9：查詢個股月營收對比表（monthly_revenue 全月份）— commit `425dda9`

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支）。
請先閱讀 AGENT.md 與 docs/spec.md（§4 鐵律、§5/§6/§7）；一律繁體中文。
嚴禁提交任何 .env 檔。工作區若有使用者未提交的變更勿動勿納入。
前置：D3/D4 已完成；本機無 Node.js：前端只寫程式碼不 build，
行為以 API 測試保障（與 spec §9 一致）。

背景：market.db 的 monthly_revenue 表——主鍵 market+code+year_month
（"YYYY-MM"），欄位 name、revenue（千元）、mom_pct（月增率%）、
yoy_pct（年增率%）、cum_revenue（累計營收千元）、cum_yoy_pct
（累計年增率%），各比率由來源 API 直接提供、缺漏容錯 NULL。
月營收為每月快照自部署起累積（目前僅 2026-06 一個月份，之後逐月遞增；
部分公司缺漏屬資料源現況，前端以空清單容錯）。apps/market 已有
MonthlyRevenue managed=False 模型與 latest_monthly_revenue selector
（D3 使用，只取最新月）。本專案依鐵律對 market 連線一律唯讀。

需求（使用者原始需求：查詢個股的資料計算範圍改依資料庫全部資料，
完善 YoY 呈現，另開表格顯示每一月份營收對比）：
1. selectors 補 monthly_revenue_rows(code)：該代號「全部」月份的列
   （year_month、revenue、mom_pct、yoy_pct、cum_revenue、cum_yoy_pct），
   依 year_month 新到舊，不設筆數上限（每檔每年至多 12 筆，量小）。
2. API：GET /api/stocks/{code}/revenue——code 驗證 4-6 位英數（不符回
   400 {"error": ...}）；回 {"code": ..., "months": [...]}，查無資料回
   200 空清單（不回 400——代號存在與否由 summary API 把關，本端點
   單純反映 monthly_revenue 現況）。整包 Redis 快取
   （key swd:v1:stock:revenue:{code}，前綴比照既有由 CACHES 加上，
   TTL 10 分鐘）。
3. 前端（/stocks/query 頁 StockQuery.vue）：summary 查詢成功（200）後
   併行呼叫本端點，於「近期資料表」下方新增區塊「月營收對比」
   Bootstrap table：月份、營收（億元，千元÷100000，兩位小數）、
   月增%、年增%、累計營收（億元）、累計年增%；NULL 顯示「—」、
   年增率紅正綠負（台股慣例）；空清單顯示「尚無月營收資料
   （自部署起逐月累積）」。revenue API 失敗不影響 summary 區塊呈現
   （獨立錯誤訊息）。
4. 既有 summary API 與快照邏輯不動（最新月指標卡維持現狀）；
   不動唯讀機制、不新增資料表。
5. 測試：selectors 全月份排序測試；API code 驗證 400、空清單 200、
   多月份輸出、快取行為測試（fixture 造多月份假資料含 NULL 欄）；
   頁面路由測試不變。

驗收：pytest 全綠（既有 115 只增不減）；ruff 無錯誤；README 查詢個股
節補月營收對比說明。完成後以 feat 前綴 commit（訊息含「D9」，結尾加
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push、
不要動 todolist.md（由管理流程更新）。
回報：改動清單（檔案與重點）、新增測試說明、測試總數、commit hash。
```

---

## ☑ D10：個股 K 線圖（還原/未還原、量與法人副圖）— commit `e646d93`

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支）。
請先完整閱讀 AGENT.md（鐵律）與 docs/spec.md §1 第三版範圍/§5/§6/§7；
一律繁體中文。工作區若有未提交變更勿動勿納入。嚴禁提交任何 .env 檔。
單元測試以 config.settings.test 執行（pytest；免真實 redis/postgres/node）；
不進行 Docker 相關測試（收尾驗收於 Docker 機統一執行）。

前置：D4 已完成。market.db 需有 daily_quotes 與 dividend_events 表。

需求：
1. apps/market 補 managed=False 模型與 selectors：institutional
   （欄位以 StockDCBot storage.py 的 CREATE TABLE 為準，逐欄核對後於
   回報列出對映表；比照 models.py 既有九模型慣例）。注意 dividend_events
   模型（DividendEvent）與 selectors.dividend_events_between 已於 D7
   存在——勿重複建模型，D10 需要按代號查事件時新增 selector 即可。
2. 前復權純邏輯 services：移植 StockDCBot analysis.adjust_history 的
   前復權演算法（由最新日往回逐除權息事件調整：除息減現金股利、除權
   除以 (1+配股率)、除權息先減再除；OHLC 四價同步調整、量不調整；
   只套用序列日期範圍內且非未來日的事件）。**公式與測試數字以 Bot 端
   tests/test_analysis.py 的案例為權威——至少移植除息/除權/除權息/
   無事件/多事件疊加五個案例且數字一致**；能讀 StockDCBot repo 時直接
   對照原始碼，不能讀時停止並回報。
3. API：GET /api/stocks/{code}/quotes?days=252&adjusted=true——
   code 4-6 位英數、days 1~252 預設 252、adjusted 預設 true；回傳
   日期舊到新的 OHLCV＋三大法人淨額（張，÷1000）序列；查無代號 400；
   Redis 快取 key swd:v1:quotes:{code}:{days}:{adjusted}，TTL 10 分鐘。
4. 前端：查詢個股頁（StockQuery.vue 流程內）在 200 結果區上方新增
   K 線卡：LwChart.vue 需擴充支援 candlestick＋histogram 副圖（成交量、
   法人淨額）；還原/未還原切換鈕（重新取 API）；互動鎖定與 fitContent
   沿用全站慣例；載入/錯誤/無資料三態。
5. 測試：前復權五案例（數字對齊 Bot 端）＋序列組裝（含法人缺日容錯）
   單元測試；API 參數驗證/快取/400 分支測試（暫時 SQLite fixture）。

驗收：pytest 全綠（既有 124 不得減少）；ruff 無錯誤。完成後以 feat 前綴
commit（訊息含「D10」，結尾加
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push。
回報：改動清單、欄位對映表、與 Bot 端測試數字對齊證明、測試數、hash。
```

## ☑ D11：產業同業比較 — commit `e48335c`

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支）。
請先完整閱讀 AGENT.md（鐵律）與 docs/spec.md §1 第三版範圍/§5/§7；
一律繁體中文。工作區若有未提交變更勿動勿納入。嚴禁提交任何 .env 檔。
單元測試以 config.settings.test 執行；不進行 Docker 相關測試。

前置：D4 已完成；StockDCBot 端 DC-M 已完成（company_profile 表：
market+code、產業別、名稱、英文簡稱——欄位以 storage.py 為準逐欄核對）。
注意：部分機器的 market.db 尚未累積此表，selectors 與 API 必須容忍
「表不存在」——回空集合與 reason 欄位，不得 500。

需求：
1. apps/market 補 company_profile 的 managed=False 模型與 selectors
   （同產業個股清單查詢；表不存在容錯）。
2. services：組裝同業對比——給定 code 找其產業別，取同產業全部個股的
   最新 valuation（PE/PB/殖利率）、monthly_revenue 最新月 YoY、
   quarterly_financials 最新季毛利率（讀取端計算），輸出對比列
   （缺值 NULL 容錯）；本股標記 is_self。
3. API：GET /api/stocks/{code}/peers——code 驗證；查無代號 400；
   company_profile 缺表/該股無產業資料時 200 回 {"peers": [],
   "reason": "..."}；Redis 快取 key swd:v1:peers:{code}，TTL 10 分鐘。
4. 前端：查詢個股頁 200 結果區新增「同業比較」摺疊卡：Bootstrap table
   對比同業（代號、名稱、PE、PB、殖利率、營收 YoY、毛利率），本股列
   高亮；reason 存在時顯示原因文字。
5. 測試：services 組裝（含缺值、單一成員、表不存在）單元測試；
   API 200/400/缺表 reason 分支測試。

驗收：pytest 全綠（不得低於既有基準）；ruff 無錯誤。完成後以 feat 前綴
commit（訊息含「D11」，結尾加
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push。
回報：改動清單、company_profile 欄位對映、測試數、hash。
```

## ☑ D12：儀表板近期警示卡 — commit `4fa091b`

```text
你的工作目錄是 StockWebDjango 專案根目錄（本 repo，git、main 分支）。
請先完整閱讀 AGENT.md（鐵律）與 docs/spec.md §1 第三版範圍/§5/§7/§10；
一律繁體中文。工作區若有未提交變更勿動勿納入。嚴禁提交任何 .env 檔。
單元測試以 config.settings.test 執行；不進行 Docker 相關測試。

前置：D2 已完成。資料來源為 StockDCBot 每日 JSON 報告
reports/YYYY-MM/taiwan_stock_report_YYYYMMDD.json。**管理者已於
2026-07-21 讀 StockDCBot repo 實檔＋原始碼（report.py／analysis.py）
核對真實結構如下，以此為準，勿再假設 [{date,type,message}] 形狀：**
- 報告頂層鍵：date（ISO "YYYY-MM-DD"）、generated_at、firm_level、
  api_status、sections。警示清單在 sections.market_alerts（list）。
- **市場級異常清單每筆為「中文鍵 dict」**，四種規則共同保證有
  `規則`、`方向`、`訊息` 三鍵（另含各規則專屬數值欄，如「佔比(%)」
  「倍數」「偏離標準差」「增減幅(%)」等，欄名不固定，勿硬取）：
  · 外資買賣超異常（方向 買超/賣超）· 跌多恐慌/漲多過熱（方向 恐慌/過熱）
  · 成交量能異常（方向 爆量/量縮）· 融資餘額異常（方向 增加/減少）。
  範例：{"規則":"成交量能異常","方向":"爆量","倍數":2.13,
  "訊息":"成交金額 8,681 億元為近 20 日均值 2.13 倍（爆量）"}。
- 每筆警示**本身不含日期**——日期取自報告頂層 date（或檔名 YYYYMMDD）。
- market_alerts 幾乎每日為空 []（無異常觸發，或掃描基準不足 60 日時降級）；
  **較舊格式報告可能沒有 market_alerts 鍵**，須以 .get("market_alerts", [])
  容錯。開發機 reports/ 目前全為空陣列（歷史短），非空樣本待部署機出現，
  故本機測試以 fixture 造非空案例驗證組裝。

需求：
1. 組態：新增 REPORTS_DIR 環境變數（.env.example 補註解；未設定或目錄
   不存在時功能優雅降級）。compose.yaml 的 web/worker 增加報告目錄
   :ro 掛載（純 JSON 讀取，無 SQLite WAL 問題）——依既有
   MARKET_DB_DIR 模式以環境變數注入。
2. services：讀最近 N 個交易日的報告 JSON（依檔名日期新到舊、最多回溯
   14 個日曆日），將每筆 market_alerts 正規化為
   {date（取自報告頂層 date）, rule（規則）, direction（方向）,
   message（訊息）}——四共同鍵缺任一則該筆以 None 容錯不跳過整檔；
   缺檔/壞 JSON/舊格式（無 market_alerts 鍵）逐檔容錯跳過並記 log，
   不得使整包失敗。
3. API：GET /api/dashboard/alerts?days=5（days 1~10）；REPORTS_DIR 未
   設定/無任何可讀報告時 200 回 {"alerts": [], "reason": "..."}；
   有可讀報告但皆無警示時 alerts 為 []、reason 為 None（非錯誤）；
   Redis 快取 key swd:v1:alerts:{days}，TTL 10 分鐘。
4. 前端：Dashboard 新增「近期市場警示」卡（第五卡，Bootstrap list）：
   依 date 分組列警示（每列顯示 rule＋direction＋message），無資料時
   顯示 reason；載入/錯誤三態。
5. 測試：services 解析單元測試（fixture 造假報告檔於 tmp_path，須含
   上述中文鍵真實形狀的非空警示案例、空陣列案例、無 market_alerts 鍵的
   舊格式案例、壞 JSON、缺檔）；API 參數驗證（days 邊界 → 400）、
   未設 REPORTS_DIR 的 reason 分支、有報告無警示的 reason=None 分支測試。

驗收：pytest 全綠（不得低於既有基準）；ruff 無錯誤。完成後以 feat 前綴
commit（訊息含「D12」，結尾加
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>），不要 push。
回報：改動清單、警示正規化欄位對映、測試數、hash。
```

---

## 已完成（記錄用）

- ✅ D0 專案骨架與環境 — commit `7e76301`（pytest 9 綠、ruff 無錯；本機無 docker/node，compose 實跑與前端 build 待有環境機器補驗，步驟見 docs/reports/D0-report.md）
- ✅ D1 外框 Navbar 與兩頁面殼 — commit `eaf9c7e`（pytest 13 綠；test 設定 django-vite 改 dev_mode=True 以免除 manifest 依賴，僅限測試設定）
- ✅ D2 首頁儀表板四圖卡＋全站白底 — commit `2d5f4fe`（pytest 27 綠；法人累積採全窗序列與 Blazor 版 W1 補強一致；前端渲染與真實 redis 待有環境補驗）
- ✅ D3 個股快照資料層 — commit `24a6791`（pytest 41 綠；欄位與 storage.py 逐欄核對一致；migration 對真實 PostgreSQL 待補驗；真實 market.db 唯讀抽查 2317/0050 正確）
- ✅ D4 查詢個股資訊頁 — commit `df886f3`（pytest 42 綠；第一版 D0-D4 全數完成）
- ✅ D5 自選股與持股頁（唯讀呈現）— commit `bea91cf`（pytest 55 綠；實機 API/頁面/空清單 200 驗證過；真實 watchlist/holdings 目前無資料，資料路徑由單元測試保障；前端渲染待有 Node 環境補驗）
- ✅ D6 法說會資訊頁（唯讀呈現）— commit `2d6a3c6`＋fix `b50981c`（pytest 73 綠；fix 為 D5 測試隔離補強：test 設定固定 WATCHLIST_USER_ID="0" 免受本機 .env 影響；實機以真實 investor_conferences 驗證 upcoming 13/recent 18、頁面 200、days=91 → 400；前端渲染待有 Node 環境補驗）
- ✅ D7 行事曆頁（月曆檢視除權息與法說會）— commit `1eaca6e`（pytest 93 綠；實機以真實資料驗證 2026-07 除權息 604/法說 16、2026-08 為 25/2、month=2019-12 → 400、頁面 200；前端月曆渲染待有 Node 環境補驗）
- ✅ D8 條件選股頁（行情＋估值複合篩選）— commit `89b7b07`（pytest 115 綠；沿用既有 latest_trade_date() 未增同義函數；實機驗證殖利率≥6+PE≤10 → 33 檔、漲幅≥9% → 10 檔、無條件/非數值 → 400、頁面 200；前端渲染待有 Node 環境補驗）
- ✅ D9 查詢個股月營收對比表（monthly_revenue 全月份）— commit `425dda9`（pytest 124 綠；full 容器重建後瀏覽器實測 2317 全流程渲染正確、億元換算正確、2330 空清單容錯；已知資料源現況：monthly_revenue TWSE 僅 942 檔、2330 缺漏，另開 Bot 端調查）
- ✅ D10 個股 K 線圖（daily_quotes 近 252 日、前復權還原/未還原、量與法人副圖）— commit `e646d93`（pytest 146 綠、ruff 乾淨；前復權五案例數字對齊 Bot 端 test_analysis.py；新增 Institutional 唯讀模型、GET /api/stocks/{code}/quotes；使用者指示免驗收直接完成；前端 K 線渲染待 Docker 機補驗）
- ✅ D11 產業同業比較（company_profile 同產業對比 PE/PB/殖利率/營收YoY/毛利率）— commit `e48335c`（管理端親跑 pytest 159 綠、ruff 乾淨；新增 CompanyProfile 唯讀模型與 GET /api/stocks/{code}/peers；company_profile 缺表以 introspection 容錯回 reason 不 500；契約唯讀掃描通過；前端同業卡渲染與缺表實測待 Docker 機補驗）
- ✅ D12 儀表板近期市場警示卡（讀 StockDCBot reports JSON 的 sections.market_alerts）— commit `4fa091b`（管理端親跑 pytest 179 綠、ruff 乾淨；派工前實讀 reports/＋report.py/analysis.py 修正 Prompt：警示為中文鍵 dict 規則/方向/訊息、日期取報告頂層 date、舊格式無鍵須 .get 容錯；新增 REPORTS_DIR 環境變數與 GET /api/dashboard/alerts；純讀檔不碰 market 連線；compose :ro 掛載、前端第五卡渲染、非空警示實檔待 Docker 機/部署機補驗——開發機 reports 歷史短皆空陣列）

### 待補驗清單（2026-07-19 大部分已於 Docker 機補驗完成）

1. ~~`docker compose --profile full up -d --build` 全套實跑~~ ✅ 已補驗——過程中修正三個 D0 遺留缺陷：
   `c7bd112`（gunicorn 鎖版 23 系列，依 spec §2 版本基準）、
   `e7dbb8d`（compose web command YAML 折疊換行截斷 gunicorn 參數致 nginx 502）、
   `4dfb84b`（market.db WAL 與 :ro 檔案掛載先天不相容——改掛目錄可寫
   `${MARKET_DB_DIR}:/data`，唯讀保證回歸連線層 query_only＋Router 雙保險；
   .env 需新增 MARKET_DB_DIR）。修正後全套五容器綠、六頁 200、
   儀表板/選股 API 以真實資料驗證正確。
2. ~~瀏覽器頁面實渲染~~ ✅ 已補驗（容器內建置的前端）——首頁四圖卡與行事曆
   月曆格線（真實除權息徽章）實際渲染正確；其餘頁另抽驗 200 與資產注入。
3. StockSnapshot migration 對真實 PostgreSQL 實跑 ✅（compose dev 驗收時已跑過）
4. 尚待：本機 `npm run dev` HMR 開發流（需裝 Node）；Celery worker 實跑抽查
   （202→快照落庫→200 全鏈路，目前由 EAGER 測試保障）
