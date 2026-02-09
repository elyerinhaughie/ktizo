<template>
  <div id="app" class="flex min-h-screen">
    <aside class="w-[250px] bg-sidebar-dark text-white flex flex-col shadow-[2px_0_4px_rgba(0,0,0,0.1)] fixed h-screen overflow-y-auto z-[1000]">
      <div class="p-6 px-4 border-b border-white/10">
        <h1 class="text-2xl font-bold text-white m-0">Ktizo</h1>
      </div>
      <nav class="flex-1 py-4 overflow-y-auto">
        <router-link to="/" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'home']" /></span>
          <span class="text-[0.95rem]">Home</span>
        </router-link>

        <!-- Kubernetes -->
        <div class="mt-4 mb-1 px-4 text-[0.7rem] font-semibold uppercase tracking-wider text-white/40">Kubernetes</div>
        <router-link to="/network" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'globe']" /></span>
          <span class="text-[0.95rem]">Network Settings</span>
        </router-link>
        <router-link to="/pxe" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'rocket']" /></span>
          <span class="text-[0.95rem]">PXE Settings</span>
        </router-link>
        <router-link to="/talos" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'microchip']" /></span>
          <span class="text-[0.95rem]">Talos Settings</span>
        </router-link>
        <router-link to="/cluster" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'cog']" /></span>
          <span class="text-[0.95rem]">Cluster Settings</span>
        </router-link>
        <router-link to="/storage" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'hard-drive']" /></span>
          <span class="text-[0.95rem]">Storage Settings</span>
        </router-link>
        <router-link to="/devices" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'desktop']" /></span>
          <span class="text-[0.95rem]">Device Management</span>
        </router-link>
        <router-link to="/terminal" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'terminal']" /></span>
          <span class="text-[0.95rem]">Terminal</span>
        </router-link>

        <!-- Applications -->
        <div class="mt-4 mb-1 px-4 text-[0.7rem] font-semibold uppercase tracking-wider text-white/40">Applications</div>
        <router-link to="/modules" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'cubes']" /></span>
          <span class="text-[0.95rem]">Modules</span>
        </router-link>
        <router-link v-if="longhornInstalled" to="/longhorn" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'hard-drive']" /></span>
          <span class="text-[0.95rem]">Longhorn</span>
        </router-link>
        <router-link v-if="arcInstalled" to="/cicd" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'code-branch']" /></span>
          <span class="text-[0.95rem]">CI/CD Runners</span>
        </router-link>

        <!-- Ktizo -->
        <div class="mt-4 mb-1 px-4 text-[0.7rem] font-semibold uppercase tracking-wider text-white/40">Ktizo</div>
        <router-link to="/wiki" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'book']" /></span>
          <span class="text-[0.95rem]">Wiki</span>
        </router-link>
        <router-link to="/troubleshooting" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'wrench']" /></span>
          <span class="text-[0.95rem]">Troubleshooting</span>
        </router-link>
        <router-link to="/audit" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'clipboard-list']" /></span>
          <span class="text-[0.95rem]">Audit Log</span>
        </router-link>
        <router-link to="/settings" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'sliders']" /></span>
          <span class="text-[0.95rem]">Settings</span>
        </router-link>
        <router-link to="/about" class="nav-item flex items-center gap-3 py-3 px-4 text-white/80 no-underline transition-all duration-300 border-l-3 border-transparent hover:bg-white/10 hover:text-white">
          <span class="text-lg w-6 text-center shrink-0"><font-awesome-icon :icon="['fas', 'circle-info']" /></span>
          <span class="text-[0.95rem]">About</span>
        </router-link>
      </nav>
      <div class="p-4 border-t border-white/10">
        <button @click="downloadKubeconfig" class="flex items-center justify-center gap-2 w-full py-3 px-4 bg-white/10 text-white border border-white/20 rounded cursor-pointer text-[0.9rem] transition-all duration-300 hover:bg-white/20 hover:border-white/30" data-tooltip="Download Kubeconfig">
          <font-awesome-icon :icon="['fas', 'download']" class="text-lg" />
          <span>Kubeconfig</span>
        </button>
      </div>
    </aside>
    <main class="flex-1 ml-[250px] p-8 max-w-[calc(100%-250px)]">
      <router-view :key="$route.path" />
    </main>

    <!-- WebSocket disconnected overlay -->
    <div v-if="!wsConnected" class="fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center" style="backdrop-filter: blur(4px);">
      <div class="bg-white rounded-lg p-8 shadow-2xl text-center max-w-sm">
        <div class="ws-spinner mx-auto mb-4"></div>
        <h3 class="text-lg font-semibold text-gray-900 m-0 mb-2">Connection Lost</h3>
        <p class="text-gray-500 text-sm m-0">Attempting to reconnect to the server...</p>
      </div>
    </div>
  </div>
</template>

<script>
import websocketService from './services/websocket'
import apiService from './services/api'
import { useToast } from 'vue-toastification'

export default {
  name: 'App',
  data() {
    return {
      wsConnected: true,
      longhornInstalled: false,
      arcInstalled: false,
    }
  },
  mounted() {
    this.toast = useToast()
    this._unsubState = websocketService.onStateChange((connected) => {
      this.wsConnected = connected
      if (connected) this.checkLonghorn()
    })
    // Initialize shared WebSocket connection
    websocketService.connect()
    // Listen for module install/uninstall events to update sidebar
    this._unsubWs = websocketService.subscribe((msg) => {
      if (msg.type === 'module_status') this.checkLonghorn()
    })
    this.checkLonghorn()
  },
  beforeUnmount() {
    if (this._unsubState) this._unsubState()
    if (this._unsubWs) this._unsubWs()
    // Disconnect WebSocket when app unmounts
    websocketService.disconnect()
  },
  methods: {
    async checkLonghorn() {
      try {
        const modules = await apiService.getModules()
        this.longhornInstalled = (modules || []).some(
          m => m.chart_name?.includes('longhorn') && m.status !== 'uninstalling'
        )
        this.arcInstalled = (modules || []).some(
          m => m.chart_name?.includes('gha-runner-scale-set-controller') && m.status !== 'uninstalling'
        )
      } catch {
        // Silently ignore — WS may not be ready yet
      }
    },
    async downloadKubeconfig() {
      try {
        // Use same hostname as current page, with port 8000
        let apiUrl = import.meta.env.VITE_API_URL
        if (!apiUrl && typeof window !== 'undefined') {
          const protocol = window.location.protocol
          const hostname = window.location.hostname
          apiUrl = `${protocol}//${hostname}:8000`
        }
        if (!apiUrl) {
          apiUrl = 'http://localhost:8000'
        }
        const response = await fetch(`${apiUrl}/api/v1/cluster/kubeconfig`)

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || 'Failed to download kubeconfig')
        }

        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'kubeconfig.yaml'
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      } catch (error) {
        console.error('Failed to download kubeconfig:', error)
        this.toast.error(error.message || 'Failed to download kubeconfig. Make sure cluster settings are configured and the cluster is running.')
      }
    }
  }
}
</script>

<style>
/* Active nav item styling - needs global scope for router-link-active */
.nav-item.router-link-active {
  background: rgba(255,255,255,0.15);
  color: white;
  border-left-color: #42b983;
  font-weight: 500;
}

.ws-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #4f46e5;
  border-radius: 50%;
  animation: ws-spin 0.8s linear infinite;
}

@keyframes ws-spin {
  to { transform: rotate(360deg); }
}
</style>
