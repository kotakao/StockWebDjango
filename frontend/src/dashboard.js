// 首頁儀表板進入點：掛載 Dashboard Vue app 至 #dashboard-app。
import { createApp } from "vue";
import Dashboard from "../components/Dashboard.vue";

const el = document.getElementById("dashboard-app");
if (el) {
  createApp(Dashboard).mount(el);
}
