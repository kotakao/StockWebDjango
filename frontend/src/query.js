// 查詢個股頁進入點：掛載 StockQuery Vue app 至 #stock-query-app。
import { createApp } from "vue";
import StockQuery from "../components/StockQuery.vue";

const el = document.getElementById("stock-query-app");
if (el) {
  createApp(StockQuery).mount(el);
}
