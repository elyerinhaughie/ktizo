<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">Troubleshooting</h2>
        <p class="text-gray-500 mt-1 mb-0">Diagnostic tools and quick fixes for common issues</p>
      </div>
      <button @click="refreshStatus" class="bg-[#42b983] text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors duration-300 hover:bg-[#35a372] disabled:bg-gray-300 disabled:cursor-not-allowed" :disabled="loadingStatus">
        <font-awesome-icon :icon="['fas', 'arrows-rotate']" :class="{ 'animate-spin': loadingStatus }" /> Refresh Status
      </button>
    </div>

    <!-- System Status -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <h3 class="text-lg font-semibold text-gray-900 mt-0 mb-4"><font-awesome-icon :icon="['fas', 'stethoscope']" class="text-blue-500 mr-2" />System Status</h3>

      <div v-if="loadingStatus && !status" class="text-center py-8 text-gray-500">
        <div class="inline-block w-6 h-6 border-3 border-gray-200 border-t-[#42b983] rounded-full animate-spin mb-3"></div>
        <p class="m-0 text-sm">Checking system status...</p>
      </div>

      <div v-else-if="status" class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div v-for="item in statusItems" :key="item.label" class="bg-gray-50 rounded-lg p-4">
          <div class="flex items-center gap-2 mb-1">
            <span class="w-2.5 h-2.5 rounded-full" :class="item.ok ? 'bg-green-500' : 'bg-red-400'"></span>
            <span class="text-sm font-medium text-gray-700">{{ item.label }}</span>
          </div>
          <div class="text-xs text-gray-400 mt-1 truncate" :title="item.detail">{{ item.detail }}</div>
        </div>
      </div>
    </div>

    <!-- Action Groups -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

      <!-- Kubectl / Kubeconfig -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h3 class="text-base font-semibold text-gray-900 mt-0 mb-1"><font-awesome-icon :icon="['fas', 'lock']" class="text-indigo-500 mr-2" />Kubernetes Access</h3>
        <p class="text-gray-400 text-xs mb-4">Fix kubectl and kubeconfig issues on this machine</p>

        <div class="space-y-3">
          <button @click="runAction('fixKubeconfig', 'troubleshootFixKubeconfig')" :disabled="running.fixKubeconfig"
            class="w-full flex items-center gap-3 p-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg cursor-pointer transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed">
            <font-awesome-icon :icon="['fas', running.fixKubeconfig ? 'arrows-rotate' : 'wrench']" class="text-gray-500 text-lg w-5" :class="{ 'animate-spin': running.fixKubeconfig }" />
            <div>
              <div class="text-sm font-medium text-gray-800">Fix Local Kubeconfig</div>
              <div class="text-xs text-gray-400">Set up ~/.talos/config and fetch ~/.kube/config from the cluster</div>
            </div>
          </button>

          <button @click="runAction('fixTalosconfig', 'troubleshootFixTalosconfig')" :disabled="running.fixTalosconfig"
            class="w-full flex items-center gap-3 p-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg cursor-pointer transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed">
            <font-awesome-icon :icon="['fas', running.fixTalosconfig ? 'arrows-rotate' : 'file-lines']" class="text-gray-500 text-lg w-5" :class="{ 'animate-spin': running.fixTalosconfig }" />
            <div>
              <div class="text-sm font-medium text-gray-800">Fix Local Talosconfig</div>
              <div class="text-xs text-gray-400">Copy talosconfig to ~/.talos/config with correct endpoints</div>
            </div>
          </button>

          <button @click="runAction('downloadKubectl', 'troubleshootDownloadKubectl')" :disabled="running.downloadKubectl"
            class="w-full flex items-center gap-3 p-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg cursor-pointer transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed">
            <font-awesome-icon :icon="['fas', running.downloadKubectl ? 'arrows-rotate' : 'download']" class="text-gray-500 text-lg w-5" :class="{ 'animate-spin': running.downloadKubectl }" />
            <div>
              <div class="text-sm font-medium text-gray-800">Reinstall kubectl</div>
              <div class="text-xs text-gray-400">Download kubectl for the configured Kubernetes version</div>
            </div>
          </button>

          <button @click="runAction('downloadTalosctl', 'troubleshootDownloadTalosctl')" :disabled="running.downloadTalosctl"
            class="w-full flex items-center gap-3 p-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg cursor-pointer transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed">
            <font-awesome-icon :icon="['fas', running.downloadTalosctl ? 'arrows-rotate' : 'download']" class="text-gray-500 text-lg w-5" :class="{ 'animate-spin': running.downloadTalosctl }" />
            <div>
              <div class="text-sm font-medium text-gray-800">Reinstall talosctl</div>
              <div class="text-xs text-gray-400">Download talosctl for the configured Talos version</div>
            </div>
          </button>
        </div>
      </div>

      <!-- Config Regeneration -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h3 class="text-base font-semibold text-gray-900 mt-0 mb-1"><font-awesome-icon :icon="['fas', 'rotate']" class="text-amber-500 mr-2" />Configuration</h3>
        <p class="text-gray-400 text-xs mb-4">Regenerate configs and PXE boot files</p>

        <div class="space-y-3">
          <button @click="runAction('regenConfigs', 'troubleshootRegenConfigs')" :disabled="running.regenConfigs"
            class="w-full flex items-center gap-3 p-3 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-lg cursor-pointer transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed">
            <font-awesome-icon :icon="['fas', running.regenConfigs ? 'arrows-rotate' : 'rotate']" class="text-amber-500 text-lg w-5" :class="{ 'animate-spin': running.regenConfigs }" />
            <div>
              <div class="text-sm font-medium text-gray-800">Regenerate All Device Configs</div>
              <div class="text-xs text-gray-400">Rebuild Talos configs for all approved devices + boot.ipxe</div>
            </div>
          </button>

          <button @click="runAction('regenDnsmasq', 'troubleshootRegenDnsmasq')" :disabled="running.regenDnsmasq"
            class="w-full flex items-center gap-3 p-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg cursor-pointer transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed">
            <font-awesome-icon :icon="['fas', running.regenDnsmasq ? 'arrows-rotate' : 'globe']" class="text-gray-500 text-lg w-5" :class="{ 'animate-spin': running.regenDnsmasq }" />
            <div>
              <div class="text-sm font-medium text-gray-800">Regenerate dnsmasq Config</div>
              <div class="text-xs text-gray-400">Recompile dnsmasq.conf from network settings and deploy</div>
            </div>
          </button>

          <button @click="runAction('restartDnsmasq', 'troubleshootRestartDnsmasq')" :disabled="running.restartDnsmasq"
            class="w-full flex items-center gap-3 p-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg cursor-pointer transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed">
            <font-awesome-icon :icon="['fas', running.restartDnsmasq ? 'arrows-rotate' : 'power-off']" class="text-gray-500 text-lg w-5" :class="{ 'animate-spin': running.restartDnsmasq }" />
            <div>
              <div class="text-sm font-medium text-gray-800">Restart dnsmasq</div>
              <div class="text-xs text-gray-400">Restart the dnsmasq DHCP/TFTP service</div>
            </div>
          </button>

          <button @click="runAction('downloadTalosFiles', 'troubleshootDownloadTalosFiles')" :disabled="running.downloadTalosFiles"
            class="w-full flex items-center gap-3 p-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg cursor-pointer transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed">
            <font-awesome-icon :icon="['fas', running.downloadTalosFiles ? 'arrows-rotate' : 'download']" class="text-gray-500 text-lg w-5" :class="{ 'animate-spin': running.downloadTalosFiles }" />
            <div>
              <div class="text-sm font-medium text-gray-800">Download Talos PXE Files</div>
              <div class="text-xs text-gray-400">Re-download vmlinuz and initramfs for the configured Talos version</div>
            </div>
          </button>

          <button @click="runAction('reinstallCni', 'troubleshootReinstallCni')" :disabled="running.reinstallCni"
            class="w-full flex items-center gap-3 p-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg cursor-pointer transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed">
            <font-awesome-icon :icon="['fas', running.reinstallCni ? 'arrows-rotate' : 'cubes']" class="text-gray-500 text-lg w-5" :class="{ 'animate-spin': running.reinstallCni }" />
            <div>
              <div class="text-sm font-medium text-gray-800">Reinstall CNI</div>
              <div class="text-xs text-gray-400">Uninstall and redeploy the configured CNI plugin (Cilium/Calico) via Helm</div>
            </div>
          </button>
        </div>
      </div>
    </div>

    <!-- Action Log -->
    <div v-if="actionLog.length" class="bg-white rounded-lg shadow-md p-6 mt-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-base font-semibold text-gray-900 m-0">Action Log</h3>
        <button @click="actionLog = []" class="text-xs text-gray-400 hover:text-gray-600 bg-transparent border-none cursor-pointer">Clear</button>
      </div>
      <div class="space-y-2 max-h-[300px] overflow-y-auto">
        <div v-for="(entry, i) in actionLog" :key="i"
          class="flex items-start gap-2 py-2 px-3 rounded text-sm"
          :class="entry.error ? 'bg-red-50' : 'bg-green-50'">
          <font-awesome-icon :icon="['fas', entry.error ? 'circle-xmark' : 'circle-check']"
            :class="entry.error ? 'text-red-400' : 'text-green-500'" class="mt-0.5 shrink-0" />
          <div class="min-w-0">
            <span class="font-medium" :class="entry.error ? 'text-red-700' : 'text-green-700'">{{ entry.label }}</span>
            <span class="text-gray-500 ml-2">{{ entry.message }}</span>
            <div class="text-xs text-gray-400 mt-0.5">{{ entry.time }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import apiService from '../services/api'
import { useToast } from 'vue-toastification'

const ACTION_LABELS = {
  fixKubeconfig: 'Fix Kubeconfig',
  fixTalosconfig: 'Fix Talosconfig',
  downloadKubectl: 'Reinstall kubectl',
  downloadTalosctl: 'Reinstall talosctl',
  regenConfigs: 'Regenerate Configs',
  regenDnsmasq: 'Regenerate dnsmasq',
  restartDnsmasq: 'Restart dnsmasq',
  downloadTalosFiles: 'Download Talos Files',
  reinstallCni: 'Reinstall CNI',
}

export default {
  name: 'Troubleshooting',
  data() {
    return {
      loadingStatus: false,
      status: null,
      running: {},
      actionLog: [],
    }
  },
  computed: {
    statusItems() {
      if (!this.status) return []
      const s = this.status
      return [
        { label: 'Kubeconfig', ok: s.kubeconfig?.exists, detail: s.kubeconfig?.exists ? s.kubeconfig.path : 'Not found' },
        { label: 'Talosconfig', ok: s.talosconfig?.exists, detail: s.talosconfig?.exists ? s.talosconfig.path : 'Not found' },
        { label: 'talosctl', ok: s.talosctl?.installed, detail: s.talosctl?.installed ? s.talosctl.version : 'Not installed' },
        { label: 'kubectl', ok: s.kubectl?.installed, detail: s.kubectl?.installed ? s.kubectl.version : 'Not installed' },
        { label: 'dnsmasq', ok: s.dnsmasq?.running, detail: s.dnsmasq?.running ? 'Running' : 'Not running' },
        { label: 'Secrets', ok: s.templates?.secrets, detail: s.templates?.secrets ? 'Generated' : 'Not generated' },
        { label: 'Cluster Config', ok: s.templates?.controlplane, detail: s.templates?.controlplane ? 'Generated' : 'Not generated' },
        { label: 'Devices', ok: s.devices?.approved > 0, detail: `${s.devices?.approved || 0} approved, ${s.devices?.pending || 0} pending` },
      ]
    },
  },
  async mounted() {
    this.toast = useToast()
    await this.refreshStatus()
  },
  methods: {
    async refreshStatus() {
      this.loadingStatus = true
      try {
        this.status = await apiService.troubleshootStatus()
      } catch (e) {
        this.toast.error(e.message || 'Failed to check status')
      } finally {
        this.loadingStatus = false
      }
    },
    async runAction(key, apiMethod) {
      this.running = { ...this.running, [key]: true }
      const label = ACTION_LABELS[key] || key
      try {
        const result = await apiService[apiMethod]()
        const message = result?.message || 'Done'
        this.toast.success(`${label}: ${message}`)
        this.actionLog.unshift({ label, message, error: false, time: new Date().toLocaleTimeString() })
        // Refresh status after any action
        this.refreshStatus()
      } catch (e) {
        const message = e.message || 'Failed'
        this.toast.error(`${label}: ${message}`)
        this.actionLog.unshift({ label, message, error: true, time: new Date().toLocaleTimeString() })
      } finally {
        this.running = { ...this.running, [key]: false }
      }
    },
  },
}
</script>
