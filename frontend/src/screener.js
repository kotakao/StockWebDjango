// 條件選股頁進入點：掛載 Screener Vue app 至 #screener-app。
import { createApp } from "vue";
import Screener from "../components/Screener.vue";

const el = document.getElementById("screener-app");
if (el) {
  createApp(Screener).mount(el);
}
