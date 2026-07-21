<script setup>
// 首頁儀表板 Vue app（spec §6）：呼叫 /api/dashboard/summary，Bootstrap grid 排四卡，
// 圖表一律經 LwChart.vue。三態 UI：載入中／錯誤／無資料。
import { computed, onMounted, ref } from "vue";
import LwChart from "./LwChart.vue";

const DAYS = 60;
const ALERTS_DAYS = 5;

const state = ref("loading"); // loading | error | empty | ready
const errorMsg = ref("");
const summary = ref(null);

// 近期市場警示卡（第五卡）：獨立三態，與四圖卡分開載入。
const alertsState = ref("loading"); // loading | error | ready
const alertsError = ref("");
const alerts = ref([]);
const alertsReason = ref(null);

// 依 date 分組（保留後端新→舊順序）。
const alertGroups = computed(() => {
  const map = new Map();
  for (const a of alerts.value) {
    if (!map.has(a.date)) map.set(a.date, []);
    map.get(a.date).push(a);
  }
  return [...map.entries()].map(([date, items]) => ({ date, items }));
});

// 將 dates + 數值陣列對齊為 LwChart 的 {time,value} 點序列。
function toSeriesData(dates, values) {
  return dates.map((time, i) => ({ time, value: values ? values[i] : null }));
}

const institutionSeries = computed(() => {
  const s = summary.value;
  if (!s) return [];
  return [
    { type: "line", color: "#d32f2f", title: "外資", data: toSeriesData(s.dates, s.institution.foreign) },
    { type: "line", color: "#1976d2", title: "投信", data: toSeriesData(s.dates, s.institution.trust) },
    { type: "line", color: "#388e3c", title: "自營商", data: toSeriesData(s.dates, s.institution.dealer) },
  ];
});

const breadthSeries = computed(() => {
  const s = summary.value;
  if (!s) return [];
  return [
    { type: "histogram", color: "#ef9a9a", title: "上漲", data: toSeriesData(s.dates, s.breadth.up) },
    { type: "histogram", color: "#a5d6a7", title: "下跌", data: toSeriesData(s.dates, s.breadth.down) },
    { type: "line", color: "#455a64", title: "A/D Line", priceScaleId: "left", data: toSeriesData(s.dates, s.breadth.ad_line) },
  ];
});

const indexSeries = computed(() => {
  const s = summary.value;
  if (!s) return [];
  return [
    { type: "line", color: "#1565c0", title: "指數收盤", data: toSeriesData(s.dates, s.index.close) },
    { type: "histogram", color: "#ffb74d", title: "成交金額(億)", priceScaleId: "left", data: toSeriesData(s.dates, s.index.turnover_100m) },
  ];
});

const marginSeries = computed(() => {
  const s = summary.value;
  if (!s) return [];
  return [
    { type: "line", color: "#6a1b9a", title: "融資餘額", data: toSeriesData(s.dates, s.margin.balance) },
  ];
});

async function load() {
  state.value = "loading";
  try {
    const resp = await fetch(`/api/dashboard/summary?days=${DAYS}`);
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    summary.value = data;
    state.value = data.count > 0 ? "ready" : "empty";
  } catch (err) {
    errorMsg.value = err.message || "載入失敗";
    state.value = "error";
  }
}

async function loadAlerts() {
  alertsState.value = "loading";
  try {
    const resp = await fetch(`/api/dashboard/alerts?days=${ALERTS_DAYS}`);
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    alerts.value = data.alerts || [];
    alertsReason.value = data.reason || null;
    alertsState.value = "ready";
  } catch (err) {
    alertsError.value = err.message || "載入失敗";
    alertsState.value = "error";
  }
}

onMounted(() => {
  load();
  loadAlerts();
});
</script>

<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h1 class="h4 mb-0">盤後儀表板</h1>
      <small class="text-muted">近 {{ DAYS }} 交易日</small>
    </div>

    <!-- 載入中 -->
    <div v-if="state === 'loading'" class="text-center text-muted py-5">
      <div class="spinner-border" role="status" aria-hidden="true"></div>
      <p class="mt-2 mb-0">載入中…</p>
    </div>

    <!-- 錯誤 -->
    <div v-else-if="state === 'error'" class="alert alert-danger" role="alert">
      載入失敗：{{ errorMsg }}
      <button type="button" class="btn btn-sm btn-outline-danger ms-2" @click="load">重試</button>
    </div>

    <!-- 無資料 -->
    <div v-else-if="state === 'empty'" class="alert alert-warning" role="alert">
      目前尚無市場資料，請待 StockDCBot 於盤後更新。
    </div>

    <!-- 資料就緒：四張圖卡 -->
    <div v-else class="row g-3">
      <div class="col-12 col-lg-6">
        <div class="card h-100">
          <div class="card-body">
            <h2 class="h6 card-title">三大法人買賣超累積（張）</h2>
            <LwChart :series="institutionSeries" />
          </div>
        </div>
      </div>
      <div class="col-12 col-lg-6">
        <div class="card h-100">
          <div class="card-body">
            <h2 class="h6 card-title">漲跌家數與 A/D Line</h2>
            <LwChart :series="breadthSeries" />
          </div>
        </div>
      </div>
      <div class="col-12 col-lg-6">
        <div class="card h-100">
          <div class="card-body">
            <h2 class="h6 card-title">指數收盤與成交金額（億元）</h2>
            <LwChart :series="indexSeries" />
          </div>
        </div>
      </div>
      <div class="col-12 col-lg-6">
        <div class="card h-100">
          <div class="card-body">
            <h2 class="h6 card-title">融資餘額趨勢</h2>
            <LwChart :series="marginSeries" />
          </div>
        </div>
      </div>
    </div>

    <!-- 第五卡：近期市場警示（獨立載入，三態；Bootstrap list） -->
    <div class="row g-3 mt-1">
      <div class="col-12">
        <div class="card">
          <div class="card-body">
            <h2 class="h6 card-title mb-3">近期市場警示（近 {{ ALERTS_DAYS }} 交易日）</h2>

            <!-- 載入中 -->
            <div v-if="alertsState === 'loading'" class="text-center text-muted py-3">
              <div class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></div>
              <span class="ms-2">載入中…</span>
            </div>

            <!-- 錯誤 -->
            <div v-else-if="alertsState === 'error'" class="alert alert-danger mb-0" role="alert">
              載入失敗：{{ alertsError }}
              <button type="button" class="btn btn-sm btn-outline-danger ms-2" @click="loadAlerts">重試</button>
            </div>

            <!-- 無警示：顯示 reason（未設定/無報告）或「近期無市場警示」 -->
            <p v-else-if="alertGroups.length === 0" class="text-muted mb-0">
              {{ alertsReason || "近期無市場警示。" }}
            </p>

            <!-- 有警示：依 date 分組列出 -->
            <div v-else>
              <div v-for="group in alertGroups" :key="group.date" class="mb-3">
                <div class="fw-semibold text-secondary small mb-1">{{ group.date }}</div>
                <ul class="list-group list-group-flush">
                  <li
                    v-for="(alert, i) in group.items"
                    :key="i"
                    class="list-group-item px-0 py-2"
                  >
                    <span class="badge text-bg-secondary me-2">{{ alert.rule || "—" }}</span>
                    <span class="badge text-bg-light border me-2">{{ alert.direction || "—" }}</span>
                    <span>{{ alert.message || "—" }}</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
