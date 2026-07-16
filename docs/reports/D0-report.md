# D0 完成回報 — 專案骨架與環境

> 派工：`todolist.md` D0（Django/DRF/Vite/Compose、雙庫與鐵律、健康檢查）
> 規格依據：`docs/spec.md` v0.1 §2/§3/§4/§8/§10/§11
> 日期：2026-07-16

**Commit**：`7e76301` — `feat: D0 專案骨架與環境（…）`（已 commit，**未 push**，trailer 為 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`）

---

## 驗收結果

| 項目 | 結果 |
|---|---|
| **pytest** | ✅ **9 passed**（health×2、router×4、鐵律唯讀×3） |
| **ruff check** | ✅ All checks passed |
| **dev runserver + /api/health** | ✅ 已實跑：default_db ok、market_db ok、redis 因本機無 redis 回 503 並附明細（邏輯正確；dev profile 有 redis 時為 200） |
| **manage.py check（dev/prod）** | ✅ 僅前端 manifest/dist 未建的預期 warning，無 error |
| **docker compose config** | ⚠️ 本機**無 docker 未實跑**；已用 PyYAML 驗證 compose.yaml 結構（5 服務、profile、anchor 皆正確）。驗證步驟見文末 |

> 本機環境限制：Python 僅 3.14.5（無 3.12；Django 5.2.16 於 3.14 可正常安裝與跑測試）、**無 node/npm、無 docker**。故前端 `npm run build` 與 docker 相關指令未於本機實跑，僅產出檔案。

---

## 結構樹

```
StockWebDjango/
├─ manage.py                     # 預設 config.settings.dev
├─ pyproject.toml                # ruff + pytest(DJANGO_SETTINGS_MODULE=config.settings.test)
├─ requirements.txt / requirements-dev.txt
├─ .env.example / .gitignore / .dockerignore
├─ Dockerfile                    # 多階段：Node22 build → python3.12-slim、非 root、collectstatic
├─ compose.yaml                  # nginx/web/worker/redis/postgres + dev/full profile
├─ docker/nginx/nginx.conf       # /static 直服、其餘反代 web:8000、security headers
├─ README.md
├─ config/
│  ├─ __init__.py（匯出 celery_app）、celery.py、routers.py（MarketRouter）
│  ├─ settings/{base,dev,prod,test}.py
│  └─ urls.py、wsgi.py、asgi.py
├─ apps/
│  ├─ core/     apps、views(HealthView)、urls、exceptions(統一400)、tasks(debug_task)、tests/test_health.py
│  ├─ market/   apps、signals(PRAGMA query_only)、models(5×managed=False)、tests/{test_router,test_readonly}.py
│  ├─ dashboard/ 空殼、stocks/ 空殼
├─ templates/base.html          # Navbar 佔位 + django-vite tags
├─ frontend/                     # package.json(鎖版)、vite.config.js、src/main.js
└─ conftest.py                   # market_db fixture（暫時 SQLite，僅建測試所需表）
```

---

## 依賴清單（皆於檔案內註明用途）

**執行時（requirements.txt）**：Django 5.2 LTS、djangorestframework、django-environ、django-redis、redis、celery、django-vite、psycopg[binary]、gunicorn

**開發／測試（requirements-dev.txt）**：pytest、pytest-django、fakeredis、ruff

**前端（frontend/package.json，鎖版）**：vue 3.5.13、bootstrap 5.3.3、lightweight-charts **4.2.3**、vite 5.4.11、@vitejs/plugin-vue 5.2.1

---

## 鐵律測試說明（spec §4.2 / §9）

唯讀採**雙保險**：

1. **連線層**（`apps/market/signals.py`）— `connection_created` signal 對 `market` 別名執行 `PRAGMA query_only=ON`，任何 DDL/DML 回 `attempt to write a readonly database`。
2. **Router 層**（`config/routers.py`）— market app 模型 `db_for_write→None`、`allow_migrate→False`。

證明測試（`apps/market/tests/test_readonly.py`）：

- `test_market_read_succeeds` — SELECT 可正常讀取。
- `test_market_insert_fails` — INSERT 拋 `OperationalError` 且訊息含 "readonly"。
- `test_market_ddl_fails` — CREATE TABLE 同樣失敗。

fixture（`conftest.py` 的 `market_db`）以獨立可寫 sqlite3 連線建暫時 schema，正式程式對 market 連線**零 DDL**。

其餘測試：

- `apps/core/tests/test_health.py` — 全連通回 200；Redis 不通回 503 並標示明細。
- `apps/market/tests/test_router.py` — market 模型讀路由 market 庫、寫入 None、非 market 模型不受接管、allow_migrate 封鎖。

---

## 待核對欄位清單

**能直接讀取 StockDCBot `storage.py` 的 `_SCHEMA`，5 張表欄位皆 1:1 精確對映，無欄位需猜測。** 僅列出留給 D2/D3 確認的**語義／部署**事項：

1. **三大法人單位**：`market_daily.foreign/trust/dealer_net` 為「股」，D2 需 ÷1000 換算「張」（storage.py `_institution_totals` 為逐股加總股數）。
2. **D3 快照對映**：spec §4.3 `revenue_yoy→yoy_pct`、`revenue_cum_yoy→cum_yoy_pct`、`revenue_month→year_month`；`gross_margin=gross_profit/revenue`、`operating_margin=operating_income/revenue`（讀取端計算）。
3. **WAL + `:ro` 掛載**：compose 依 spec 以單檔 `:ro` 掛載 market.db；bot 端為 WAL 模式，跨容器唯讀讀取若遇 `-wal` sidecar 可見性問題，未來可改為掛載其父目錄。D2 實跑資料時留意。

### market.db 對映表（D0 已建 managed=False 模型）

| 模型 | db_table | 欄位 | 主鍵 |
|---|---|---|---|
| `DailyQuote` | daily_quotes | market,date,code,name,open,high,low,close,change,volume | (market,date,code) |
| `Valuation` | valuation | market,date,code,pe,dividend_yield,pb | (market,date,code) |
| `MarketDaily` | market_daily | market,date,index_close,index_change_pct,turnover,up_count,down_count,foreign_net,trust_net,dealer_net,margin_balance,short_balance | (market,date) |
| `MonthlyRevenue` | monthly_revenue | market,code,year_month,name,revenue,mom_pct,yoy_pct,cum_revenue,cum_yoy_pct | (market,code,year_month) |
| `QuarterlyFinancial` | quarterly_financials | market,code,year_quarter,name,revenue,gross_profit,operating_income,net_income,eps | (market,code,year_quarter) |

（複合主鍵以 Django 5.2 `CompositePrimaryKey` 表示；TEXT→CharField、REAL→FloatField，全數值欄容錯 NULL。）

---

## 測試數

**9 passed**（health 2、router 4、鐵律唯讀 3）；ruff 無錯誤。

執行指令：

```bash
.venv/Scripts/python -m pytest      # settings=config.settings.test，無需 postgres/redis/docker
.venv/Scripts/ruff check .
```

測試以 `config.settings.test` 執行：`default` 用 in-memory SQLite、`market` 由 conftest fixture 注入暫時檔、Redis 用 fakeredis（`FakeRedisConnection`，`ping()` 可真實回應）。

---

## docker compose 驗證步驟（本機無 docker，待有 docker 環境執行）

```bash
cp .env.example .env                          # 填 MARKET_DB_PATH 等
docker compose --profile full config          # 驗證語法
docker compose --profile dev up -d             # 僅 redis+postgres（宿主機 runserver）
docker compose --profile full up -d --build    # 全套（nginx/web/worker/redis/postgres）
```

> 註：Compose profile 語意無法同時滿足「plain `up`=全套」與「`--profile dev`=子集」，故 full/dev 皆以明確 `--profile` 指定（README 已說明，略異於 AGENT.md 的一行式）。

---

## 環境備忘（已存入專案 memory）

- **本機工具鏈**：Python 3.14、無 node/docker；測試用 test settings + fakeredis 免依賴跑綠。
- **market.db 權威 schema**：`StockDCBot/storage.py` 的 `_SCHEMA` 常數（本機可讀），欄位對映見上表。
