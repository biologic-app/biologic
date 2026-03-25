import '@/assets/css/main.css'
import { createApp } from 'vue'
import ui from '@nuxt/ui/vue-plugin'
import App from '@/app/App.vue'
import { router } from '@/app/router'
import { i18n } from '@/shared/i18n'
import { createPinia } from 'pinia'

const pinia = createPinia()
const app = createApp(App)

app.use(router)
app.use(pinia)
app.use(i18n)
app.use(ui)

app.mount('#app')

