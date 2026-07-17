<script setup>
// 自選股 Vue app（spec §6、派工 D5）：GET /api/watchlist/summary → 兩區塊表格。
// 唯讀呈現：自選股（收盤/漲跌%/PE/PB/殖利率）與持股（股數/均價/收盤/市值/未實現/報酬率）。
// 紅漲綠跌（台股慣例）、NULL 顯示「—」；載入中/錯誤/空清單三態；編輯入口不在本頁。
import { computed, onMounted, ref } from "vue";

const state = ref("loading"); // loading | ready | error
const errorMsg = ref("");
const data = ref(null);

const watchlist = computed(() => data.value?.watchlist ?? []);
const holdings = computed(() => data.value?.holdings ?? []);
const isEmpty = computed(
  () => watchlist.value.length === 0 && holdings.value.length === 0,
);

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

async function load() {
  state.value = "loading";
  try {
    const resp = await fetch("/api/watchlist/summary");
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      errorMsg.value = body.error || `HTTP ${resp.status}`;
      state.value = "error";
      return;
    }
    data.value = await resp.json();
    state.value = "ready";
  } catch (err) {
    errorMsg.value = err.message || "載入失敗";
    state.value = "error";
  }
}

onMounted(load);
</script>

<template>
  <div>
    <h1 class="h4 mb-3">自選股與持股</h1>

    <!-- 載入中 -->
    <div v-if="state === 'loading'" class="text-center text-muted py-5">
      <div class="spinner-border" role="status" aria-hidden="true"></div>
      <p class="mt-2 mb-0">載入中…</p>
    </div>

    <!-- 錯誤 -->
    <div v-else-if="state === 'error'" class="alert alert-danger" role="alert">
      {{ errorMsg }}
      <button type="button" class="btn btn-sm btn-outline-danger ms-2" @click="load">
        重試
      </button>
    </div>

    <!-- 空清單 -->
    <div v-else-if="isEmpty" class="alert alert-info" role="alert">
      尚無自選股或持股資料。
    </div>

    <!-- 資料就緒 -->
    <div v-else>
      <!-- 自選股 -->
      <h2 class="h5 mb-2">自選股</h2>
      <div v-if="watchlist.length === 0" class="text-muted mb-4">尚無自選股。</div>
      <div v-else class="table-responsive mb-4">
        <table class="table table-sm table-striped align-middle">
          <thead>
            <tr>
              <th>代號</th>
              <th class="text-end">收盤</th>
              <th class="text-end">漲跌%</th>
              <th class="text-end">PE</th>
              <th class="text-end">PB</th>
              <th class="text-end">殖利率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in watchlist" :key="row.code">
              <td>{{ row.code }}</td>
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

      <!-- 持股 -->
      <h2 class="h5 mb-2">持股</h2>
      <div v-if="holdings.length === 0" class="text-muted mb-4">尚無持股。</div>
      <div v-else class="table-responsive mb-4">
        <table class="table table-sm table-striped align-middle">
          <thead>
            <tr>
              <th>代號</th>
              <th class="text-end">股數</th>
              <th class="text-end">均價</th>
              <th class="text-end">收盤</th>
              <th class="text-end">市值</th>
              <th class="text-end">未實現損益</th>
              <th class="text-end">報酬率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in holdings" :key="row.code">
              <td>{{ row.code }}</td>
              <td class="text-end">{{ fmtNum(row.shares, 0) }}</td>
              <td class="text-end">{{ fmtNum(row.avg_cost) }}</td>
              <td class="text-end">{{ fmtNum(row.close) }}</td>
              <td class="text-end">{{ fmtNum(row.market_value, 0) }}</td>
              <td class="text-end" :class="changeClass(row.unrealized_pnl)">
                {{ fmtNum(row.unrealized_pnl, 0) }}
              </td>
              <td class="text-end" :class="changeClass(row.return_pct)">
                {{ fmtPct(row.return_pct) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 頁尾：編輯入口說明（本頁唯讀） -->
    <p class="text-muted mt-3">
      <small>編輯請於 Discord /watch 或 Blazor 版操作；本頁僅唯讀呈現。</small>
    </p>
  </div>
</template>
