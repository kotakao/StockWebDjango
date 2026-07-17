// 自選股頁進入點：掛載 Watchlist Vue app 至 #watchlist-app。
import { createApp } from "vue";
import Watchlist from "../components/Watchlist.vue";

const el = document.getElementById("watchlist-app");
if (el) {
  createApp(Watchlist).mount(el);
}
