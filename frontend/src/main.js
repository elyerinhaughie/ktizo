import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'
import './assets/main.css'

import { library } from '@fortawesome/fontawesome-svg-core'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
  faHome, faGlobe, faCog, faHardDrive, faDesktop, faBook, faTerminal,
  faDownload, faCheck, faCircleCheck, faXmark, faCircleXmark, faRocket,
  faCircleInfo, faLightbulb, faChartBar, faCompactDisc, faTrash,
  faSortUp, faSortDown, faPlus, faPen, faTriangleExclamation,
  faSearch, faFilter, faArrowRight, faClipboardList,
  faChevronDown, faChevronRight, faSliders, faPowerOff, faBolt, faMicrochip,
  faCubes, faLock, faCodeBranch, faCube, faArrowsRotate, faClock, faDatabase,
  faWrench, faStethoscope, faRotate, faFileLines, faArrowUpRightFromSquare,
  faPlay, faLayerGroup, faShieldHalved, faUserShield, faDiagramProject,
  faExpand, faCompress
} from '@fortawesome/free-solid-svg-icons'

library.add(
  faHome, faGlobe, faCog, faHardDrive, faDesktop, faBook, faTerminal,
  faDownload, faCheck, faCircleCheck, faXmark, faCircleXmark, faRocket,
  faCircleInfo, faLightbulb, faChartBar, faCompactDisc, faTrash,
  faSortUp, faSortDown, faPlus, faPen, faTriangleExclamation,
  faSearch, faFilter, faArrowRight, faClipboardList,
  faChevronDown, faChevronRight, faSliders, faPowerOff, faBolt, faMicrochip,
  faCubes, faLock, faCodeBranch, faCube, faArrowsRotate, faClock, faDatabase,
  faWrench, faStethoscope, faRotate, faFileLines, faArrowUpRightFromSquare,
  faPlay, faLayerGroup, faShieldHalved, faUserShield, faDiagramProject,
  faExpand, faCompress
)

import themeService from './services/theme'
themeService.initTheme()

import App from './App.vue'
import Home from './views/Home.vue'
import NetworkSettings from './views/NetworkSettings.vue'
import PxeSettings from './views/PxeSettings.vue'
import ClusterSettings from './views/ClusterSettings.vue'
import TalosSettings from './views/TalosSettings.vue'
import StorageSettings from './views/StorageSettings.vue'
import DeviceManagement from './views/DeviceManagement.vue'
import Modules from './views/Modules.vue'
import LonghornManagement from './views/LonghornManagement.vue'
import Wiki from './views/Wiki.vue'
import Terminal from './views/Terminal.vue'
import About from './views/About.vue'
import Settings from './views/Settings.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/network', name: 'NetworkSettings', component: NetworkSettings },
  { path: '/pxe', name: 'PxeSettings', component: PxeSettings },
  { path: '/talos', name: 'TalosSettings', component: TalosSettings },
  { path: '/cluster', name: 'ClusterSettings', component: ClusterSettings },
  { path: '/storage', name: 'StorageSettings', component: StorageSettings },
  { path: '/devices', name: 'DeviceManagement', component: DeviceManagement },
  { path: '/modules', redirect: '/modules/cluster' },
  { path: '/modules/cluster', name: 'ModulesCluster', component: Modules },
  { path: '/modules/applications', name: 'ModulesApplications', component: Modules },
  { path: '/longhorn', name: 'LonghornManagement', component: LonghornManagement },
  { path: '/rbac', name: 'RbacManagement', component: () => import('./views/RbacManagement.vue') },
  { path: '/workloads', name: 'WorkloadGraph', component: () => import('./views/WorkloadManagement.vue') },
  { path: '/cicd', name: 'CiCdRunners', component: () => import('./views/CiCdRunners.vue') },
  { path: '/wiki', name: 'Wiki', component: Wiki },
  { path: '/terminal', name: 'Terminal', component: Terminal },
  { path: '/troubleshooting', name: 'Troubleshooting', component: () => import('./views/Troubleshooting.vue') },
  { path: '/audit', name: 'AuditLog', component: () => import('./views/AuditLog.vue') },
  { path: '/settings', name: 'Settings', component: Settings },
  { path: '/about', name: 'About', component: About }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to) {
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth' }
    }
    return { top: 0 }
  }
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
app.component('font-awesome-icon', FontAwesomeIcon)
app.use(router)
app.use(Toast, toastOptions)
app.mount('#app')
