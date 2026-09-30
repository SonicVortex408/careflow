import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          charts: ["recharts"],
          markdown: ["react-markdown", "remark-gfm"],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: false,
  },
});
