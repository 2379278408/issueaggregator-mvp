import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiBasePath = (env.VITE_API_BASE_PATH || '/api').trim().replace(/\/$/, '') || '/api'
  const apiProxyTarget = (env.VITE_API_PROXY_TARGET || 'http://localhost:8000').trim()

  return {
    plugins: [vue()],
    server: {
      allowedHosts: ['.monkeycode-ai.online'],
      proxy: {
        [apiBasePath]: {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
    },
    test: {
      environment: 'jsdom',
      globals: true,
      include: ['src/**/*.test.ts'],
    },
  }
})
