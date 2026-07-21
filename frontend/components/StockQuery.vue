<script setup>
// 查詢個股 Vue app（spec §6、派工 D4）：代號輸入 → GET /api/stocks/{code}/summary。
// 202 處理中：以 1 秒間隔輪詢（上限 10 次，逾時顯示錯誤與重試）；400 顯示 API 錯誤。
// 200：指標卡列（收盤/漲跌%、PE、PB、殖利率、月營收 YoY、累計營收 YoY、毛利率、
// 營益率、EPS，各標資料基準，NULL 顯示「—」）＋近 20 交易日快照表。
import { computed, onUnmounted, ref } from "vue";
import LwChart from "./LwChart.vue";

const CODE_RE = /^[A-Za-z0-9]{4,6}$/; // 前端先驗：4-6 位英數
const MAX_POLL = 10; // 202 輪詢上限
const POLL_INTERVAL = 1000; // 1 秒
const KLINE_DAYS = 252; // K 線近 252 交易日

const codeInput = ref("");
const queriedCode = ref("");
const state = ref("idle"); // idle | loading | processing | ready | error | timeout
const errorMsg = ref("");
const result = ref(null);
const pollCount = ref(0);
let timer = null;

const latest = computed(() => result.value?.latest ?? null);
const recent = computed(() => result.value?.recent ?? []);

// 月營收對比（獨立狀態，失敗不影響 summary 區塊）
const revenueMonths = ref([]);
const revenueError = ref("");

// K 線（獨立狀態，失敗不影響 summary 區塊）；adjusted 切換即重新取 API。
const klineState = ref("idle"); // idle | loading | ready | empty | error
const klineError = ref("");
const klineAdjusted = ref(true);
const quotes = ref([]);

// 同業比較（獨立狀態，失敗不影響 summary 區塊）；摺疊卡預設展開。
const peersState = ref("idle"); // idle | loading | ready | empty | error
const peersError = ref("");
const peers = ref([]);
const peersReason = ref("");
const peersOpen = ref(true);

// LwChart series：candlestick 主圖 ＋ 成交量、法人淨額兩個 histogram 副圖（分層 scaleMargins）。
const klineSeries = computed(() => {
  const rows = quotes.value;
  if (!rows.length) return [];
  return [
    {
      type: "candlestick",
      priceScaleId: "right",
      scaleMargins: { top: 0.05, bottom: 0.45 },
      data: rows.map((r) => ({
        time: r.date,
        open: r.open,
        high: r.high,
        low: r.low,
        close: r.close,
      })),
    },
    {
      type: "histogram",
      color: "#90a4ae",
      title: "成交量(張)",
      priceScaleId: "volume",
      scaleMargins: { top: 0.6, bottom: 0.25 },
      // 成交股數 ÷1000 → 張；缺值保留 null 由 LwChart 轉缺口。
      data: rows.map((r) => ({
        time: r.date,
        value: r.volume === null || r.volume === undefined ? null : Math.round(r.volume / 1000),
      })),
    },
    {
      type: "histogram",
      title: "法人淨額(張)",
      priceScaleId: "inst",
      scaleMargins: { top: 0.8, bottom: 0 },
      // 紅買綠賣（台股慣例）；缺日保留 null。
      data: rows.map((r) => ({
        time: r.date,
        value: r.inst_net,
        color: r.inst_net === null || r.inst_net === undefined
          ? undefined
          : r.inst_net >= 0
            ? "#ef9a9a"
            : "#a5d6a7",
      })),
    },
  ];
});

// 數值格式化：NULL/undefined 一律顯示「—」。
function fmtNum(v, digits = 2) {
  return v === null || v === undefined ? "—" : Number(v).toFixed(digits);
}
function fmtPct(v, digits = 2) {
  return v === null || v === undefined ? "—" : `${Number(v).toFixed(digits)}%`;
}
// 千元 → 億元（÷100000），兩位小數；NULL/undefined 顯示「—」。
function fmtYi(v) {
  return v === null || v === undefined ? "—" : (Number(v) / 100000).toFixed(2);
}
// 漲跌色（台股慣例：紅漲綠跌）；0 或缺值不上色。
function changeClass(v) {
  if (v === null || v === undefined || v === 0) return "";
  return v > 0 ? "text-danger" : "text-success";
}

// 指標卡設定：由 latest 動態產生（每卡標註資料基準）。
const cards = computed(() => {
  const s = latest.value;
  if (!s) return [];
  const tradeBasis = `交易日 ${s.trade_date ?? "—"}`;
  const revBasis = `營收月份 ${s.revenue_month ?? "—"}`;
  const finBasis = `財報季 ${s.quarter ?? "—"}`;
  return [
    {
      title: "收盤 / 漲跌%",
      value: fmtNum(s.close),
      sub: fmtPct(s.change_pct),
      subClass: changeClass(s.change_pct),
      basis: tradeBasis,
    },
    { title: "本益比 (PE)", value: fmtNum(s.pe), basis: tradeBasis },
    { title: "股價淨值比 (PB)", value: fmtNum(s.pb), basis: tradeBasis },
    { title: "殖利率", value: fmtPct(s.dividend_yield), basis: tradeBasis },
    { title: "月營收 YoY", value: fmtPct(s.revenue_yoy), basis: revBasis },
    { title: "累計營收 YoY", value: fmtPct(s.revenue_cum_yoy), basis: revBasis },
    { title: "毛利率", value: fmtPct(s.gross_margin), basis: finBasis },
    { title: "營業利益率", value: fmtPct(s.operating_margin), basis: finBasis },
    { title: "EPS", value: fmtNum(s.eps), basis: finBasis },
  ];
});

function clearTimer() {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
}

async function runFetch(code) {
  try {
    const resp = await fetch(`/api/stocks/${encodeURIComponent(code)}/summary`);
    if (resp.status === 202) {
      if (pollCount.value >= MAX_POLL) {
        state.value = "timeout";
        return;
      }
      pollCount.value += 1;
      state.value = "processing";
      timer = setTimeout(() => runFetch(code), POLL_INTERVAL);
      return;
    }
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      errorMsg.value = body.error || `HTTP ${resp.status}`;
      state.value = "error";
      return;
    }
    result.value = await resp.json();
    state.value = "ready";
    fetchRevenue(code); // summary 就緒後併行取月營收（失敗不影響上方）
    fetchQuotes(code); // 併行取日 K（失敗不影響上方）
    fetchPeers(code); // 併行取同業比較（失敗不影響上方）
  } catch (err) {
    errorMsg.value = err.message || "載入失敗";
    state.value = "error";
  }
}

// 月營收對比：獨立呼叫，錯誤僅記在 revenueError，不動 summary 區塊。
async function fetchRevenue(code) {
  revenueError.value = "";
  revenueMonths.value = [];
  try {
    const resp = await fetch(`/api/stocks/${encodeURIComponent(code)}/revenue`);
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      revenueError.value = body.error || `HTTP ${resp.status}`;
      return;
    }
    const data = await resp.json();
    revenueMonths.value = data.months ?? [];
  } catch (err) {
    revenueError.value = err.message || "月營收載入失敗";
  }
}

// 日 K：獨立呼叫，錯誤僅記在 klineError，不動 summary 區塊。adjusted 依切換鈕。
async function fetchQuotes(code) {
  klineState.value = "loading";
  klineError.value = "";
  quotes.value = [];
  try {
    const url = `/api/stocks/${encodeURIComponent(code)}/quotes?days=${KLINE_DAYS}&adjusted=${klineAdjusted.value}`;
    const resp = await fetch(url);
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      klineError.value = body.error || `HTTP ${resp.status}`;
      klineState.value = "error";
      return;
    }
    const data = await resp.json();
    quotes.value = data.quotes ?? [];
    klineState.value = quotes.value.length ? "ready" : "empty";
  } catch (err) {
    klineError.value = err.message || "K 線載入失敗";
    klineState.value = "error";
  }
}

// 還原/未還原切換：翻轉 adjusted 後重新取 API（重繪整張圖）。
function toggleAdjust() {
  klineAdjusted.value = !klineAdjusted.value;
  if (queriedCode.value) fetchQuotes(queriedCode.value);
}

// 同業比較：獨立呼叫，錯誤僅記在 peersError，不動 summary 區塊。
// 200 可能回 {"peers": [], "reason": ...}（缺表/無產業資料），以 reason 顯示原因。
async function fetchPeers(code) {
  peersState.value = "loading";
  peersError.value = "";
  peers.value = [];
  peersReason.value = "";
  try {
    const resp = await fetch(`/api/stocks/${encodeURIComponent(code)}/peers`);
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      peersError.value = body.error || `HTTP ${resp.status}`;
      peersState.value = "error";
      return;
    }
    const data = await resp.json();
    peers.value = data.peers ?? [];
    peersReason.value = data.reason || "";
    peersState.value = peers.value.length ? "ready" : "empty";
  } catch (err) {
    peersError.value = err.message || "同業比較載入失敗";
    peersState.value = "error";
  }
}

function submit() {
  const code = codeInput.value.trim();
  if (!CODE_RE.test(code)) {
    errorMsg.value = "代號需為 4-6 位英數";
    state.value = "error";
    return;
  }
  clearTimer();
  pollCount.value = 0;
  result.value = null;
  revenueMonths.value = [];
  revenueError.value = "";
  quotes.value = [];
  klineState.value = "idle";
  peers.value = [];
  peersReason.value = "";
  peersState.value = "idle";
  queriedCode.value = code;
  state.value = "loading";
  runFetch(code);
}

function retry() {
  if (!queriedCode.value) return;
  clearTimer();
  pollCount.value = 0;
  state.value = "loading";
  runFetch(queriedCode.value);
}

onUnmounted(clearTimer);
</script>

<template>
  <div>
    <h1 class="h4 mb-3">查詢個股</h1>

    <form class="row g-2 mb-3" @submit.prevent="submit">
      <div class="col-auto">
        <label class="visually-hidden" for="stockCode">股票代號</label>
        <input
          id="stockCode"
          v-model="codeInput"
          type="text"
          class="form-control"
          placeholder="股票代號（4-6 位英數）"
          maxlength="6"
          autocomplete="off"
        />
      </div>
      <div class="col-auto">
        <button type="submit" class="btn btn-primary">查詢</button>
      </div>
    </form>

    <!-- 載入中 -->
    <div v-if="state === 'loading'" class="text-center text-muted py-5">
      <div class="spinner-border" role="status" aria-hidden="true"></div>
      <p class="mt-2 mb-0">載入中…</p>
    </div>

    <!-- 彙整中（202 輪詢） -->
    <div v-else-if="state === 'processing'" class="text-center text-muted py-5">
      <div class="spinner-border" role="status" aria-hidden="true"></div>
      <p class="mt-2 mb-0">彙整中…（{{ pollCount }}/{{ MAX_POLL }}）</p>
    </div>

    <!-- 逾時 -->
    <div v-else-if="state === 'timeout'" class="alert alert-warning" role="alert">
      彙整逾時，請稍後再試。
      <button type="button" class="btn btn-sm btn-outline-warning ms-2" @click="retry">
        重試
      </button>
    </div>

    <!-- 錯誤 -->
    <div v-else-if="state === 'error'" class="alert alert-danger" role="alert">
      {{ errorMsg }}
    </div>

    <!-- 資料就緒 -->
    <div v-else-if="state === 'ready' && latest">
      <div class="d-flex align-items-baseline mb-3">
        <h2 class="h5 mb-0">{{ latest.code }}</h2>
        <span v-if="latest.name" class="text-muted ms-2">{{ latest.name }}</span>
        <span v-if="latest.market" class="badge text-bg-secondary ms-2">{{ latest.market }}</span>
      </div>

      <!-- K 線卡（daily_quotes 近 252 日；成交量、法人淨額副圖；還原/未還原切換） -->
      <div class="card mb-4">
        <div class="card-body">
          <div class="d-flex align-items-center justify-content-between mb-2">
            <h2 class="h6 card-title mb-0">
              日 K 線（近 {{ KLINE_DAYS }} 交易日）
              <small class="text-muted ms-1">{{ klineAdjusted ? "還原" : "未還原" }}</small>
            </h2>
            <button
              type="button"
              class="btn btn-sm btn-outline-secondary"
              :disabled="klineState === 'loading'"
              @click="toggleAdjust"
            >
              切換為{{ klineAdjusted ? "未還原" : "還原" }}
            </button>
          </div>

          <!-- 載入中 -->
          <div v-if="klineState === 'loading'" class="text-center text-muted py-5">
            <div class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></div>
            <span class="ms-2">K 線載入中…</span>
          </div>
          <!-- 錯誤 -->
          <div v-else-if="klineState === 'error'" class="alert alert-warning py-2 mb-0" role="alert">
            K 線載入失敗：{{ klineError }}
          </div>
          <!-- 無資料 -->
          <p v-else-if="klineState === 'empty'" class="text-muted mb-0">尚無日 K 資料。</p>
          <!-- 就緒 -->
          <LwChart v-else-if="klineState === 'ready'" :series="klineSeries" :height="360" />

          <p class="text-muted small mb-0 mt-2">
            主圖為日 K，副圖由上而下為成交量（張）、三大法人淨額（張，紅買綠賣）。
          </p>
        </div>
      </div>

      <!-- 指標卡列 -->
      <div class="row g-3 mb-4">
        <div v-for="c in cards" :key="c.title" class="col-6 col-md-4 col-lg-3">
          <div class="card h-100">
            <div class="card-body">
              <h3 class="h6 card-title text-muted">{{ c.title }}</h3>
              <p class="fs-4 mb-1">
                {{ c.value }}
                <span v-if="c.sub" :class="c.subClass">{{ c.sub }}</span>
              </p>
              <small class="text-muted">{{ c.basis }}</small>
            </div>
          </div>
        </div>
      </div>

      <!-- 近 20 交易日快照 -->
      <h2 class="h6 mb-2">近期資料（近 {{ recent.length }} 個交易日）</h2>
      <div class="table-responsive">
        <table class="table table-sm table-striped align-middle">
          <thead>
            <tr>
              <th>日期</th>
              <th class="text-end">收盤</th>
              <th class="text-end">漲跌%</th>
              <th class="text-end">PE</th>
              <th class="text-end">PB</th>
              <th class="text-end">殖利率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in recent" :key="row.trade_date">
              <td>{{ row.trade_date }}</td>
              <td class="text-end">{{ fmtNum(row.close) }}</td>
              <td class="text-end" :class="changeClass(row.change_pct)">
                {{ fmtPct(row.change_pct) }}
              </td>
              <td class="text-end">{{ fmtNum(row.pe) }}</td>
              <td class="text-end">{{ fmtNum(row.pb) }}</td>
              <td class="text-end">{{ fmtPct(row.dividend_yield) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 月營收對比（monthly_revenue 全月份，新到舊） -->
      <h2 class="h6 mb-2 mt-4">月營收對比</h2>
      <div v-if="revenueError" class="alert alert-warning py-2" role="alert">
        月營收載入失敗：{{ revenueError }}
      </div>
      <p v-else-if="revenueMonths.length === 0" class="text-muted">
        尚無月營收資料（自部署起逐月累積）
      </p>
      <div v-else class="table-responsive">
        <table class="table table-sm table-striped align-middle">
          <thead>
            <tr>
              <th>月份</th>
              <th class="text-end">營收（億元）</th>
              <th class="text-end">月增%</th>
              <th class="text-end">年增%</th>
              <th class="text-end">累計營收（億元）</th>
              <th class="text-end">累計年增%</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in revenueMonths" :key="m.year_month">
              <td>{{ m.year_month }}</td>
              <td class="text-end">{{ fmtYi(m.revenue) }}</td>
              <td class="text-end">{{ fmtPct(m.mom_pct) }}</td>
              <td class="text-end" :class="changeClass(m.yoy_pct)">{{ fmtPct(m.yoy_pct) }}</td>
              <td class="text-end">{{ fmtYi(m.cum_revenue) }}</td>
              <td class="text-end" :class="changeClass(m.cum_yoy_pct)">{{ fmtPct(m.cum_yoy_pct) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 同業比較（company_profile 同產業個股對比；本股列高亮，摺疊卡） -->
      <div class="card mt-4">
        <div class="card-header d-flex align-items-center justify-content-between">
          <h2 class="h6 mb-0">同業比較</h2>
          <button
            type="button"
            class="btn btn-sm btn-outline-secondary"
            :aria-expanded="peersOpen"
            @click="peersOpen = !peersOpen"
          >
            {{ peersOpen ? "收合" : "展開" }}
          </button>
        </div>
        <div v-show="peersOpen" class="card-body">
          <!-- 載入中 -->
          <div v-if="peersState === 'loading'" class="text-center text-muted py-3">
            <div class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></div>
            <span class="ms-2">同業比較載入中…</span>
          </div>
          <!-- 錯誤 -->
          <div v-else-if="peersState === 'error'" class="alert alert-warning py-2 mb-0" role="alert">
            同業比較載入失敗：{{ peersError }}
          </div>
          <!-- 無資料（含缺表/無產業資料，以 reason 顯示原因） -->
          <p v-else-if="peersState === 'empty'" class="text-muted mb-0">
            {{ peersReason || "尚無同業資料" }}
          </p>
          <!-- 就緒 -->
          <template v-else-if="peersState === 'ready'">
            <p v-if="peersReason" class="text-muted small mb-2">{{ peersReason }}</p>
            <div class="table-responsive">
              <table class="table table-sm table-striped align-middle mb-0">
                <thead>
                  <tr>
                    <th>代號</th>
                    <th>名稱</th>
                    <th class="text-end">PE</th>
                    <th class="text-end">PB</th>
                    <th class="text-end">殖利率</th>
                    <th class="text-end">營收 YoY</th>
                    <th class="text-end">毛利率</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="p in peers"
                    :key="p.code"
                    :class="{ 'table-warning fw-semibold': p.is_self }"
                  >
                    <td>{{ p.code }}</td>
                    <td>{{ p.name || "—" }}</td>
                    <td class="text-end">{{ fmtNum(p.pe) }}</td>
                    <td class="text-end">{{ fmtNum(p.pb) }}</td>
                    <td class="text-end">{{ fmtPct(p.dividend_yield) }}</td>
                    <td class="text-end" :class="changeClass(p.revenue_yoy)">
                      {{ fmtPct(p.revenue_yoy) }}
                    </td>
                    <td class="text-end">{{ fmtPct(p.gross_margin) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
