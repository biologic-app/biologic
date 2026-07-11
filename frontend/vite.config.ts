import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import VueDevTools from 'vite-plugin-vue-devtools'
import ui from '@nuxt/ui/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({ mode }) => ({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
    dedupe: ['@iconify/vue']
  },
  plugins: [
    vue(),
    ...(mode !== 'production' ? [VueDevTools()] : []),
    ui({
      ui: {
        colors: {
          primary: 'green',
          neutral: 'zinc'
        }
      }
    }),
    VitePWA({
      // injectManifest (not generateSW): sw.ts owns its `push` /
      // `notificationclick` handlers by hand — generateSW only knows how to
      // emit a precaching worker, it has no hook for custom event listeners.
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.ts',
      registerType: 'autoUpdate',
      injectRegister: false,
      includeAssets: ['logo.svg'],
      manifest: {
        name: 'Biologic LIMS',
        short_name: 'Biologic',
        description:
          'Biologic LIMS is a laboratory information management system designed to streamline and optimize laboratory workflows: samples, research, protocols and reporting.',
        theme_color: '#ffffff',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' }
        ]
      },
      injectManifest: {
        // The generated dist/ has hashed chunk names in the thousands; the
        // default (~2 MiB) budget undercounts a Nuxt UI build long before
        // precaching is actually a problem.
        maximumFileSizeToCacheInBytes: 6 * 1024 * 1024
      },
      devOptions: {
        // Kept off in dev: Vite's dev server already serves everything
        // uncached, and a dev-mode SW would fight vue-devtools' HMR socket.
        enabled: false,
        type: 'module'
      }
    })
  ]
}))
