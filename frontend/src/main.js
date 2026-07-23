import { createApp } from 'vue'
import { setConfig, frappeRequest, resourcesPlugin } from 'frappe-ui'
import App from './App.vue'
import router from './router'
import './index.css'
import '@/components/builder/controls.css'

setConfig('resourceFetcher', frappeRequest)

const app = createApp(App)
app.use(router)
app.use(resourcesPlugin)
app.mount('#app')
