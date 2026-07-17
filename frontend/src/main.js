// 前端進入點（D0 骨架）：載入 Bootstrap 樣式與 JS。
// 各頁 Vue app 與圖表元件（LwChart.vue）於 D1+ 掛載。
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap";
// 全站樣式（body 白底，作用於所有頁面）
import "./styles.css";

// 佔位：確認建置鏈可用；實際頁面邏輯於後續派工實作。
console.info("StockWeb frontend bundle loaded.");
