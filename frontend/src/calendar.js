// 行事曆頁進入點：掛載 Calendar Vue app 至 #calendar-app。
import { createApp } from "vue";
import Calendar from "../components/Calendar.vue";

const el = document.getElementById("calendar-app");
if (el) {
  createApp(Calendar).mount(el);
}
