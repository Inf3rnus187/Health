import react from '@vitejs/plugin-react';
import { defineConfig, type Plugin } from 'vite';

// One id per build: baked into the app and written to /version.json, so
// an open page sees that a newer build was installed (« Recharger »).
const BUILD_ID = new Date().toISOString();

function versionFile(): Plugin {
  return {
    name: 'version-file',
    apply: 'build',
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'version.json',
        source: JSON.stringify({ build: BUILD_ID }),
      });
    },
  };
}

// During `pnpm dev`, proxy API calls to the local backend. In production
// Nginx serves the build and proxies /api itself.
export default defineConfig({
  plugins: [react(), versionFile()],
  define: {
    __BUILD_ID__: JSON.stringify(BUILD_ID),
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
