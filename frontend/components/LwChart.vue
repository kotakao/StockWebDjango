<script setup>
// 全站唯一圖表入口（spec §6）：包裝 TradingView Lightweight Charts 4.2.3。
// 儀表板驗收鐵律——鎖定互動：handleScroll:false、handleScale:false，
// 資料範圍以 fitContent() 固定（滑鼠拖動、滾輪縮放、觸控平移全部無效）。
import { createChart } from "lightweight-charts";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  // series：[{ type:'line'|'histogram'|'candlestick', color, data, priceScaleId?, title?,
  //           scaleMargins?, upColor?, downColor? }]
  //   line/histogram data：[{time,value|null,color?}]
  //   candlestick data：[{time,open,high,low,close}]（缺 close 視為 whitespace 缺口）
  //   scaleMargins：{top,bottom} 套用於該 series 的 priceScaleId，供 K 線＋成交量/法人副圖分層
  series: { type: Array, required: true },
  height: { type: Number, default: 220 },
});

const container = ref(null);
let chart = null;
let resizeObserver = null;

// null 值轉為 whitespace 資料點（{time} 無值）→ 缺口不臆造數值；candlestick 以 close 判缺。
function toPoints(data) {
  return data.map((p) => {
    if (p.open !== undefined) {
      return p.close === null || p.close === undefined ? { time: p.time } : p;
    }
    return p.value === null || p.value === undefined ? { time: p.time } : p;
  });
}

function buildChart() {
  if (!container.value) return;
  disposeChart();

  chart = createChart(container.value, {
    height: props.height,
    width: container.value.clientWidth,
    layout: { background: { color: "#ffffff" }, textColor: "#333333" },
    grid: { horzLines: { color: "#f0f0f0" }, vertLines: { color: "#f7f7f7" } },
    rightPriceScale: { borderColor: "#e0e0e0" },
    timeScale: { borderColor: "#e0e0e0", fixLeftEdge: true, fixRightEdge: true },
    // 鎖定互動（驗收項）：拖動、縮放、觸控全關。
    handleScroll: false,
    handleScale: false,
    kineticScroll: { mouse: false, touch: false },
  });

  // 若任一 series 指定左軸，開啟左價格軸。
  if (props.series.some((s) => s.priceScaleId === "left")) {
    chart.applyOptions({ leftPriceScale: { visible: true, borderColor: "#e0e0e0" } });
  }

  for (const s of props.series) {
    let chartSeries;
    if (s.type === "candlestick") {
      // 台股慣例：紅漲綠跌。
      const up = s.upColor || "#d32f2f";
      const down = s.downColor || "#388e3c";
      chartSeries = chart.addCandlestickSeries({
        upColor: up,
        downColor: down,
        borderUpColor: up,
        borderDownColor: down,
        wickUpColor: up,
        wickDownColor: down,
        priceScaleId: s.priceScaleId || "right",
        priceLineVisible: false,
        lastValueVisible: true,
      });
    } else {
      const opts = {
        color: s.color,
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
      };
      if (s.priceScaleId) opts.priceScaleId = s.priceScaleId;
      if (s.title) opts.title = s.title;
      chartSeries =
        s.type === "histogram" ? chart.addHistogramSeries(opts) : chart.addLineSeries(opts);
    }
    chartSeries.setData(toPoints(s.data || []));
    // 副圖分層：以 scaleMargins 將該 series 的價格軸壓到指定範圍（如成交量置底）。
    if (s.scaleMargins && s.priceScaleId) {
      chart.priceScale(s.priceScaleId).applyOptions({ scaleMargins: s.scaleMargins });
    }
  }

  // 固定資料範圍（不可平移/縮放）。
  chart.timeScale().fitContent();
}

function disposeChart() {
  if (chart) {
    chart.remove();
    chart = null;
  }
}

onMounted(() => {
  buildChart();
  // 僅隨容器寬度自適應；重繪後仍 fitContent，維持固定範圍。
  resizeObserver = new ResizeObserver(() => {
    if (chart && container.value) {
      chart.applyOptions({ width: container.value.clientWidth });
      chart.timeScale().fitContent();
    }
  });
  if (container.value) resizeObserver.observe(container.value);
});

watch(
  () => props.series,
  () => buildChart(),
  { deep: true },
);

onBeforeUnmount(() => {
  if (resizeObserver) resizeObserver.disconnect();
  disposeChart();
});
</script>

<template>
  <div ref="container" class="lw-chart"></div>
</template>

<style scoped>
.lw-chart {
  width: 100%;
}
</style>
