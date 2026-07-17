<script setup>
// 查詢個股 Vue app（spec §6、派工 D4）：代號輸入 → GET /api/stocks/{code}/summary。
// 202 處理中：以 1 秒間隔輪詢（上限 10 次，逾時顯示錯誤與重試）；400 顯示 API 錯誤。
// 200：指標卡列（收盤/漲跌%、PE、PB、殖利率、月營收 YoY、累計營收 YoY、毛利率、
// 營益率、EPS，各標資料基準，NULL 顯示「—」）＋近 20 交易日快照表。
import { computed, onUnmounted, ref } from "vue";

const CODE_RE = /^[A-Za-z0-9]{4,6}$/; // 前端先驗：4-6 位英數
const MAX_POLL = 10; // 202 輪詢上限
const POLL_INTERVAL = 1000; // 1 秒

const codeInput = ref("");
const queriedCode = ref("");
const state = ref("idle"); // idle | loading | processing | ready | error | timeout
const errorMsg = ref("");
const result = ref(null);
const pollCount = ref(0);
let timer = null;

const latest = computed(() => result.value?.latest ?? null);
const recent = computed(() => result.value?.recent ?? []);

// 數值格式化：NULL/undefined 一律顯示「—」。
function fmtNum(v, digits = 2) {
  return v === null || v === undefined ? "—" : Number(v).toFixed(digits);
}
function fmtPct(v, digits = 2) {
  return v === null || v === undefined ? "—" : `${Number(v).toFixed(digits)}%`;
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
  } catch (err) {
    errorMsg.value = err.message || "載入失敗";
    state.value = "error";
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
    </div>
  </div>
</template>
