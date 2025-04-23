import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import monacoEditorPlugin from 'vite-plugin-monaco-editor';
import { analyzer } from 'vite-bundle-analyzer';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Configure Monaco Editor plugin to use workers and minimize initial load
    monacoEditorPlugin({
      globalAPI: false, // Don't expose the entire API globally
      languageWorkers: [
        'typescript'
      ], // Only load necessary language workers
      customWorkers: [],
    }),
    analyzer({ analyzerMode: 'static', fileName: 'bundle-analyzer' }),
  ],

  css: {
    modules: {
      localsConvention: 'camelCase',
    },
  },
  resolve: {
    alias: {
      '@src': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    cors: true,
  },
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    // Optimize chunk size
    chunkSizeWarningLimit: 1000, // Increase warning limit to reduce noise
    minify: 'esbuild',
    rollupOptions: {
      input: {
        main: './index.html',
        electron: './electron/main.js'
      },
      output: {
        entryFileNames: (chunkInfo) => {
          return chunkInfo.name === 'electron' ? '[name].js' : 'assets/[name]-[hash].js';
        },
        // Manually split chunks for better caching and smaller bundles
        manualChunks: {
          // Split vendor chunks
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-redux': ['react-redux', '@reduxjs/toolkit'],
          'vendor-ui': ['antd', '@ant-design/icons'],
          // Split Monaco Editor into separate chunks
          'monaco-editor-core': ['monaco-editor/esm/vs/editor/editor.api'],
        },
        // Optimize asset file naming for better caching
        assetFileNames: (assetInfo) => {
          const extType = assetInfo.names?.[0]?.split('.')?.at(1);
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType || '')) {
            return `assets/images/[name]-[hash][extname]`;
          }
          return `assets/[name]-[hash][extname]`;
        },
      },
    },
  },
});
