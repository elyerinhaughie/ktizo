import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'
import App from './App.vue'
import Home from './views/Home.vue'
import NetworkSettings from './views/NetworkSettings.vue'
import ClusterSettings from './views/ClusterSettings.vue'
import StorageSettings from './views/StorageSettings.vue'
import DeviceManagement from './views/DeviceManagement.vue'
import Wiki from './views/Wiki.vue'
import Terminal from './views/Terminal.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/network', name: 'NetworkSettings', component: NetworkSettings },
  { path: '/cluster', name: 'ClusterSettings', component: ClusterSettings },
  { path: '/storage', name: 'StorageSettings', component: StorageSettings },
  { path: '/devices', name: 'DeviceManagement', component: DeviceManagement },
  { path: '/wiki', name: 'Wiki', component: Wiki },
  { path: '/terminal', name: 'Terminal', component: Terminal }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const toastOptions = {
  position: 'bottom-right',
  timeout: 5000,
  closeOnClick: true,
  pauseOnFocusLoss: true,
  pauseOnHover: true,
  draggable: true,
  draggablePercent: 0.6,
  showCloseButtonOnHover: false,
  hideProgressBar: false,
  closeButton: 'button',
  icon: true,
  rtl: false
}

const app = createApp(App)
app.use(router)
app.use(Toast, toastOptions)
app.mount('#app')
