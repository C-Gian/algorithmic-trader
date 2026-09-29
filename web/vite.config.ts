import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies the API; production build is served by FastAPI.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
