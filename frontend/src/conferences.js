// 法說會頁進入點：掛載 Conferences Vue app 至 #conferences-app。
import { createApp } from "vue";
import Conferences from "../components/Conferences.vue";

const el = document.getElementById("conferences-app");
if (el) {
  createApp(Conferences).mount(el);
}
