<script setup>
// 行事曆 Vue app（spec §6、派工 D7）：GET /api/calendar/summary?month=YYYY-MM
// → 月曆格線（週一至週日七欄）呈現除權息與法說會日期。
// 月曆組格為純前端邏輯（spec §9 不做前端單元測試）；上/下月切換即重新呼叫 API。
import { computed, onMounted, ref } from "vue";

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];
const today = new Date();
const todayIso = toIso(today.getFullYear(), today.getMonth() + 1, today.getDate());

const state = ref("loading"); // loading | ready | error
const errorMsg = ref("");
const data = ref(null);
// 目前檢視的年月（預設當月）。
const year = ref(today.getFullYear());
const month = ref(today.getMonth() + 1); // 1~12

const monthStr = computed(() => `${year.value}-${String(month.value).padStart(2, "0")}`);
const title = computed(() => `${year.value} 年 ${month.value} 月`);

function toIso(y, m, d) {
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

// 缺值一律顯示「—」。
function dash(v) {
  return v === null || v === undefined || v === "" ? "—" : v;
}

// 依日期字串（YYYY-MM-DD）取「日」數。
function dayOf(iso) {
  return iso ? parseInt(iso.slice(8, 10), 10) : null;
}

// 除權息徽章 title：公司名＋配息/配股。
function dividendTitle(ev) {
  const parts = [dash(ev.name)];
  if (ev.cash_dividend != null) parts.push(`配息 ${ev.cash_dividend}`);
  if (ev.stock_ratio != null) parts.push(`配股 ${ev.stock_ratio}`);
  return parts.join("　");
}

// 月曆格線：週一起始，補前置空格，依「日」歸集當日事件。
const weeks = computed(() => {
  const y = year.value;
  const m = month.value;
  const dividends = data.value?.dividends ?? [];
  const conferences = data.value?.conferences ?? [];

  // 依日歸集
  const byDay = {};
  for (const ev of dividends) {
    const d = dayOf(ev.ex_date);
    if (d) (byDay[d] ??= { dividends: [], conferences: [] }).dividends.push(ev);
  }
  for (const cf of conferences) {
    const d = dayOf(cf.fact_date);
    if (d) (byDay[d] ??= { dividends: [], conferences: [] }).conferences.push(cf);
  }

  const daysInMonth = new Date(y, m, 0).getDate();
  const firstDow = (new Date(y, m - 1, 1).getDay() + 6) % 7; // 週一=0

  const cells = [];
  for (let i = 0; i < firstDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({
      day: d,
      iso: toIso(y, m, d),
      dividends: byDay[d]?.dividends ?? [],
      conferences: byDay[d]?.conferences ?? [],
    });
  }
  while (cells.length % 7 !== 0) cells.push(null);

  const rows = [];
  for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7));
  return rows;
});

const isEmpty = computed(
  () => (data.value?.dividends?.length ?? 0) === 0 &&
    (data.value?.conferences?.length ?? 0) === 0,
);

async function load() {
  state.value = "loading";
  try {
    const resp = await fetch(`/api/calendar/summary?month=${monthStr.value}`);
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

function shift(delta) {
  let m = month.value + delta;
  let y = year.value;
  if (m < 1) {
    m = 12;
    y -= 1;
  } else if (m > 12) {
    m = 1;
    y += 1;
  }
  year.value = y;
  month.value = m;
  load();
}

onMounted(load);
</script>

<template>
  <div>
    <div class="d-flex align-items-center mb-3">
      <h1 class="h4 mb-0 me-auto">行事曆</h1>
      <button type="button" class="btn btn-outline-secondary btn-sm" @click="shift(-1)">
        上一月
      </button>
      <span class="mx-3 fw-bold">{{ title }}</span>
      <button type="button" class="btn btn-outline-secondary btn-sm" @click="shift(1)">
        下一月
      </button>
    </div>

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

    <!-- 資料就緒：月曆格線 -->
    <div v-else>
      <div v-if="isEmpty" class="alert alert-info" role="alert">
        本月無除權息或法說會事件。
      </div>

      <div class="table-responsive">
        <table class="table table-bordered text-center align-top mb-0">
          <thead>
            <tr>
              <th v-for="w in WEEKDAYS" :key="w" class="w-14">{{ w }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in weeks" :key="`w-${ri}`">
              <td
                v-for="(cell, ci) in row"
                :key="`c-${ri}-${ci}`"
                class="calendar-cell"
                :class="{ 'table-warning': cell && cell.iso === todayIso }"
              >
                <template v-if="cell">
                  <div class="text-muted small mb-1">{{ cell.day }}</div>
                  <span
                    v-for="(ev, i) in cell.dividends"
                    :key="`d-${i}`"
                    class="badge bg-danger d-block text-truncate mb-1"
                    :title="dividendTitle(ev)"
                  >{{ dash(ev.event_type) }} {{ ev.code }}</span>
                  <span
                    v-for="(cf, i) in cell.conferences"
                    :key="`f-${i}`"
                    class="badge bg-primary d-block text-truncate mb-1"
                    :title="`${dash(cf.name)}　${dash(cf.subject)}`"
                  >法說 {{ cf.code }}</span>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 頁尾：資料性質註記 -->
      <p class="text-muted mt-3">
        <small>
          除權息來自每交易日盤後入庫；法說會為每日快照過濾入庫、自部署起累積。本頁唯讀呈現。
        </small>
      </p>
    </div>
  </div>
</template>

<style scoped>
.calendar-cell {
  height: 6rem;
  width: 14.28%;
  vertical-align: top;
  font-size: 0.85rem;
}
</style>
