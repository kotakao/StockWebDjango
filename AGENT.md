# AGENTS.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- If you write 200 lines and it could be 50, rewrite it.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

- Don't "improve" adjacent code, comments, or formatting.
- Match existing style, even if you'd do it differently.
- Remove imports/variables/functions that YOUR changes made unused; don't remove pre-existing dead code unless asked.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"

## 5. Always use Traditional Chinese for all responses.

---

--- project-doc ---

# StockWebDjango — 台股盤後研究網頁（Django 版）

## 專案定位

單人使用的**盤後**研究工具。資料由姊妹專案 **StockDCBot**（Python Discord Bot，本機路徑見下方「本機路徑」節）每交易日 17:00 後寫入 SQLite `market.db`；本專案負責查詢、彙整與視覺化。另有 .NET Blazor 版姊妹專案 StockWeb 並行存在。系統規格：`docs/spec.md`；開發派工：`todolist.md`。

## 技術棧

Python 3.12／Django 5.2 LTS／DRF／PostgreSQL 16（自有資料）＋ SQLite market.db（唯讀）／Redis＋Celery／Bootstrap 5.3＋Vue 3.5（Vite）／Lightweight Charts 4.2.3／Gunicorn＋Nginx／Docker Compose。分層規約見 `docs/spec.md` §3.2（selectors 唯讀查詢、services 純邏輯、views 薄層、Vue 只取數渲染）。

## 鐵律（與 StockDCBot 的資料庫共用契約，違反即為錯誤）

1. **`market.db` 的 schema 歸 StockDCBot（storage.py）獨占管理**。本專案對 `market` 連線嚴禁任何 CREATE/ALTER/DROP/INSERT/UPDATE/DELETE；需要新市場資料表時，回 StockDCBot 開 DC-x 派工。（測試 fixture 建暫時 SQLite 檔不在此限。）
2. `market` 連線唯讀開啟＋Database Router 雙保險（`managed=False`、`allow_migrate=False`、寫入路由 None）；必須有「寫入會失敗」的證明測試。
3. Django 自有資料（stock_snapshots、sessions 等）一律在 PostgreSQL（`default`），嚴禁建入 market.db。
4. 機密與路徑走環境變數：`.env` 嚴禁提交（`.env.example` 除外）；`MARKET_DB_PATH`／`DATABASE_URL`／`REDIS_URL`／`SECRET_KEY` 不得寫死在程式或文件。
5. 兩專案依賴 SQLite **WAL 模式**（由 Bot 端開啟）。

## 工程慣例

- API 驗證：code 4-6 位英數、days 1~252；錯誤一律 400 `{"error": "..."}`，不回 500。
- Redis key 前綴 `swd:v1:`；Celery task 必須冪等、留 log、可重試。
- 圖表一律經 `frontend/components/LwChart.vue`，不得另建圖表入口。
- 測試：pytest；services/selectors 全覆蓋；全綠才 commit。lint：ruff。
- commit：`feat:`/`fix:`/`chore:`/`docs:` 前綴＋繁中摘要，結尾加
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`，**不要 push**（push 由管理流程統一執行）。

## 本機路徑（雙機開發，本節內容不隨 commit 更新——依政策各機自行維護）

- StockDCBot repo：`D:\01 DevProgram\00 Self-Project\StockDCBot`
- market.db：`D:\01 DevProgram\00 Self-Project\StockDCBot\data\market.db`（`.env` 的 `MARKET_DB_PATH` 指向此處）

## 建置與測試

```bash
# 開發（dev profile：容器跑 redis/postgres，宿主機跑 Django）
docker compose --profile dev up -d
python manage.py runserver

# 全套
docker compose up -d

# 測試與 lint
pytest
ruff check .
```
