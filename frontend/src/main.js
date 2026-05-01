import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { initAuth } from './stores/authStore'
import './style.css'

const app = createApp(App)
app.use(router)

initAuth().then(() => {
  app.mount('#app')
})
