import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "node:path";

// django-vite 整合：base 對齊 Django STATIC_URL，產物含 manifest 供後端注入。
export default defineConfig({
  plugins: [vue()],
  base: "/static/",
  build: {
    manifest: true,
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "src/main.js"),
        dashboard: resolve(__dirname, "src/dashboard.js"),
        query: resolve(__dirname, "src/query.js"),
        watchlist: resolve(__dirname, "src/watchlist.js"),
        conferences: resolve(__dirname, "src/conferences.js"),
        calendar: resolve(__dirname, "src/calendar.js"),
        screener: resolve(__dirname, "src/screener.js"),
      },
    },
  },
  server: {
    host: "localhost",
    port: 5173,
    origin: "http://localhost:5173",
  },
});
