import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    proxy: {
      // Même origine que l'API en dev : le cookie de refresh (httpOnly, path /api/auth/) suit sans CORS.
      // `changeOrigin: false` garde `Host: localhost`, seul hôte accepté par l'API de dev (pas `web`).
      "/api": { target: process.env.API_PROXY_TARGET ?? "http://localhost:8000", changeOrigin: false },
    },
  },
  build: { target: "es2020", sourcemap: true },
  test: { globals: true, environment: "jsdom", setupFiles: ["./src/test-setup.ts"], css: false },
});
