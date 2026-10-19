import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The project shipped `@vitejs/plugin-react` as a dependency but had no Vite config at all, so it
// was never loaded: JSX built only because esbuild handles .jsx by default, and Fast Refresh never
// worked. The dev proxy matters more. Without it the browser called the API cross-origin on
// :8000 and depended on the backend's CORS list, so dev and production took different code paths
// through `API_BASE`. Both now use a same-origin `/api`.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  preview: { host: '127.0.0.1', port: 4173 },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.js'],
    include: ['src/**/*.test.{js,jsx}'],
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        // Keep the vendor bundle separate so an app change does not invalidate React in cache.
        manualChunks: { react: ['react', 'react-dom'], icons: ['lucide-react'] },
      },
    },
  },
});
