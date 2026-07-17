<script setup>
// 法說會 Vue app（spec §6、派工 D6）：GET /api/conferences/summary → 兩區塊表格。
// 唯讀呈現：即將召開（召開日/代號/公司/主旨）與近期公告（發言日/代號/公司/主旨）。
// NULL 顯示「—」；載入中/錯誤/空清單三態；資料性質註記於頁尾。
import { computed, onMounted, ref } from "vue";

const state = ref("loading"); // loading | ready | error
const errorMsg = ref("");
const data = ref(null);

const upcoming = computed(() => data.value?.upcoming ?? []);
const recent = computed(() => data.value?.recent ?? []);
const isEmpty = computed(
  () => upcoming.value.length === 0 && recent.value.length === 0,
);

// 缺值（NULL/undefined/空字串）一律顯示「—」。
function dash(v) {
  return v === null || v === undefined || v === "" ? "—" : v;
}

async function load() {
  state.value = "loading";
  try {
    const resp = await fetch("/api/conferences/summary?days=30");
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
    <h1 class="h4 mb-3">法說會資訊</h1>

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
      尚無法說會資料。
    </div>

    <!-- 資料就緒 -->
    <div v-else>
      <!-- 即將召開 -->
      <h2 class="h5 mb-2">即將召開（未來 30 日）</h2>
      <div v-if="upcoming.length === 0" class="text-muted mb-4">近期無即將召開的法說會。</div>
      <div v-else class="table-responsive mb-4">
        <table class="table table-sm table-striped align-middle">
          <thead>
            <tr>
              <th>召開日</th>
              <th>代號</th>
              <th>公司</th>
              <th>主旨</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in upcoming" :key="`u-${row.code}-${i}`">
              <td>{{ dash(row.fact_date) }}</td>
              <td>{{ dash(row.code) }}</td>
              <td>{{ dash(row.name) }}</td>
              <td>{{ dash(row.subject) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 近期公告 -->
      <h2 class="h5 mb-2">近期公告</h2>
      <div v-if="recent.length === 0" class="text-muted mb-4">尚無近期公告。</div>
      <div v-else class="table-responsive mb-4">
        <table class="table table-sm table-striped align-middle">
          <thead>
            <tr>
              <th>發言日</th>
              <th>代號</th>
              <th>公司</th>
              <th>主旨</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in recent" :key="`r-${row.code}-${i}`">
              <td>{{ dash(row.announce_date) }}</td>
              <td>{{ dash(row.code) }}</td>
              <td>{{ dash(row.name) }}</td>
              <td>{{ dash(row.subject) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 頁尾：資料性質註記 -->
    <p class="text-muted mt-3">
      <small>
        資料為每日快照過濾入庫、自部署起累積，僅含主旨含「法人說明會」之公告；本頁唯讀呈現。
      </small>
    </p>
  </div>
</template>
