import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@features': resolve(__dirname, 'src/features'),
      '@components': resolve(__dirname, 'src/components'),
      '@hooks': resolve(__dirname, 'src/hooks'),
      '@services': resolve(__dirname, 'src/services'),
      '@config': resolve(__dirname, 'src/config'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@types': resolve(__dirname, 'src/types'),
    },
  },

  // Development server configuration
  server: {
    port: 5173,
    open: false,
    cors: true,
    proxy: {
      // Proxy API requests to backend during development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },

  // Build optimization
  build: {
    target: 'es2022',
    sourcemap: true,

    // Rollup options for chunk optimization
    rollupOptions: {
      output: {
        manualChunks: {
          // Monaco Editor should be in its own chunk (5MB)
          'monaco-editor': ['@monaco-editor/react'],

          // Chakra UI components
          'chakra-ui': [
            '@chakra-ui/react',
            '@chakra-ui/icons',
            '@emotion/react',
            '@emotion/styled',
          ],

          // React core
          'react-vendor': ['react', 'react-dom'],

          // Utility libraries
          'utils': [
            'axios',
            'dompurify',
            'react-syntax-highlighter',
          ],
        },

        // Generate meaningful chunk names
        chunkFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId
            ? chunkInfo.facadeModuleId.split('/').pop()
            : 'chunk';
          return `assets/${facadeModuleId}-[hash].js`;
        },
      },
    },

    // Chunk size warning threshold (Monaco is large)
    chunkSizeWarningLimit: 5000, // 5MB (Monaco is ~5MB)
  },

  // Optimize dependencies
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      '@chakra-ui/react',
      '@emotion/react',
      '@emotion/styled',
      'axios',
    ],
    // Exclude Monaco from pre-bundling (lazy load)
    exclude: ['@monaco-editor/react'],
  },
})