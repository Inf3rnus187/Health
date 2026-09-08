import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// During `pnpm dev`, proxy API calls to the local backend. In production
// Nginx serves the build and proxies /api itself.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
