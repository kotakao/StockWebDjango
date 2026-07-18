<script setup>
// 條件選股 Vue app（spec §6、派工 D8）：GET /api/screener/results
// → 最新交易日行情＋估值複合條件篩選結果表。
// 條件全部選填、皆數字輸入；查詢前擋「全部留空」；紅漲綠跌、NULL 顯示「—」。
import { computed, reactive, ref } from "vue";

// 條件表單（空字串＝未指定）。key 對齊 API query 參數。
const form = reactive({
  pe_min: "",
  pe_max: "",
  pb_min: "",
  pb_max: "",
  yield_min: "",
  change_pct_min: "",
  change_pct_max: "",
  volume_lots_min: "",
});

const state = ref("idle"); // idle | loading | ready | error
const errorMsg = ref("");
const data = ref(null);

const hasAnyFilter = computed(() =>
  Object.values(form).some((v) => v !== "" && v !== null),
);

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

const results = computed(() => data.value?.results ?? []);
const total = computed(() => data.value?.total ?? 0);

async function load() {
  if (!hasAnyFilter.value) {
    errorMsg.value = "至少需指定一個篩選條件";
    state.value = "error";
    return;
  }
  state.value = "loading";
  const params = new URLSearchParams();
  for (const [key, val] of Object.entries(form)) {
    if (val !== "" && val !== null) params.append(key, val);
  }
  try {
    const resp = await fetch(`/api/screener/results?${params.toString()}`);
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
</script>

<template>
  <div>
    <h1 class="h4 mb-3">條件選股</h1>

    <!-- 條件表單 -->
    <form class="row g-3 mb-4" @submit.prevent="load">
      <div class="col-6 col-md-3">
        <label class="form-label">PE 下限</label>
        <input v-model="form.pe_min" type="number" step="any" class="form-control" />
      </div>
      <div class="col-6 col-md-3">
        <label class="form-label">PE 上限</label>
        <input v-model="form.pe_max" type="number" step="any" class="form-control" />
      </div>
      <div class="col-6 col-md-3">
        <label class="form-label">PB 下限</label>
        <input v-model="form.pb_min" type="number" step="any" class="form-control" />
      </div>
      <div class="col-6 col-md-3">
        <label class="form-label">PB 上限</label>
        <input v-model="form.pb_max" type="number" step="any" class="form-control" />
      </div>
      <div class="col-6 col-md-3">
        <label class="form-label">殖利率下限 (%)</label>
        <input v-model="form.yield_min" type="number" step="any" class="form-control" />
      </div>
      <div class="col-6 col-md-3">
        <label class="form-label">漲跌% 下限</label>
        <input v-model="form.change_pct_min" type="number" step="any" class="form-control" />
      </div>
      <div class="col-6 col-md-3">
        <label class="form-label">漲跌% 上限</label>
        <input v-model="form.change_pct_max" type="number" step="any" class="form-control" />
      </div>
      <div class="col-6 col-md-3">
        <label class="form-label">成交張數下限</label>
        <input v-model="form.volume_lots_min" type="number" step="any" class="form-control" />
      </div>
      <div class="col-12">
        <button type="submit" class="btn btn-primary" :disabled="!hasAnyFilter">
          查詢
        </button>
        <span v-if="!hasAnyFilter" class="text-muted ms-2">請至少指定一個條件。</span>
      </div>
    </form>

    <!-- 載入中 -->
    <div v-if="state === 'loading'" class="text-center text-muted py-5">
      <div class="spinner-border" role="status" aria-hidden="true"></div>
      <p class="mt-2 mb-0">載入中…</p>
    </div>

    <!-- 錯誤 -->
    <div v-else-if="state === 'error'" class="alert alert-danger" role="alert">
      {{ errorMsg }}
    </div>

    <!-- 資料就緒 -->
    <div v-else-if="state === 'ready'">
      <p class="text-muted">
        符合 {{ total }} 檔（顯示前 200）
        <span v-if="data.date">・交易日 {{ data.date }}</span>
      </p>

      <div v-if="results.length === 0" class="alert alert-info" role="alert">
        無符合條件的個股。
      </div>

      <div v-else class="table-responsive">
        <table class="table table-sm table-striped align-middle">
          <thead>
            <tr>
              <th>代號</th>
              <th>名稱</th>
              <th class="text-end">收盤</th>
              <th class="text-end">漲跌%</th>
              <th class="text-end">PE</th>
              <th class="text-end">PB</th>
              <th class="text-end">殖利率</th>
              <th class="text-end">成交張數</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in results" :key="`${row.market}-${row.code}`">
              <td>{{ row.code }}</td>
              <td>{{ row.name ?? "—" }}</td>
              <td class="text-end">{{ fmtNum(row.close) }}</td>
              <td class="text-end" :class="changeClass(row.change_pct)">
                {{ fmtPct(row.change_pct) }}
              </td>
              <td class="text-end">{{ fmtNum(row.pe) }}</td>
              <td class="text-end">{{ fmtNum(row.pb) }}</td>
              <td class="text-end">{{ fmtPct(row.dividend_yield) }}</td>
              <td class="text-end">{{ fmtNum(row.volume_lots, 0) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <p class="text-muted mt-3">
      <small>
        以最新交易日 daily_quotes 行情與同日 valuation 估值複合篩選；本頁唯讀
        （依鐵律，本專案對 market 連線一律唯讀）。
      </small>
    </p>
  </div>
</template>
