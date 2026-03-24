import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueRouter from 'vue-router/vite'
import vueLayouts from 'vite-plugin-vue-layouts'
import VueDevTools from 'vite-plugin-vue-devtools'
import ui from '@nuxt/ui/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vueRouter({
      dts: 'src/route-map.d.ts'
    }),
    vueLayouts(),
    vue(),
    VueDevTools(),
    ui({
      ui: {
        colors: {
          primary: 'green',
          neutral: 'zinc'
        }
      }
    }),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['logo.svg'],

      manifest: {
        name: 'Biologic-LIMS',
        short_name: 'biologic-lims',
        description: 'biologic-lims is a laboratory information management system (LIMS) designed to streamline and optimize laboratory workflows. It provides a comprehensive solution for managing samples, experiments, data, and reporting in a laboratory setting.',
        theme_color: '#ffffff',
        
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' }
        ]
      },
      devOptions: {
        enabled: false
      }
    })
  ]
})
