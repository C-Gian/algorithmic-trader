/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Single local frontend, no remote assets at runtime. /api goes to the local APP-001 service on
// loopback (started together with Vite by `npm run dev`); Host and Origin are forwarded unchanged.
export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy: { '/api': { target: 'http://127.0.0.1:8765', changeOrigin: false } } },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: ['src/test-setup.ts'],
  },
});
