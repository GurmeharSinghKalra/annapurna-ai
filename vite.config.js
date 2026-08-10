import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The React plugin was a dependency but was never wired up, so dev had no Fast
// Refresh. `appType: 'spa'` keeps the dev server's history fallback explicit,
// matching the nginx try_files rule used in the production image.
export default defineConfig({
  plugins: [react()],
  appType: 'spa',
  server: {
    host: '127.0.0.1',
    port: 5173
  },
  preview: {
    host: '127.0.0.1',
    port: 4173
  },
  build: {
    outDir: 'dist',
    sourcemap: false
  }
});
