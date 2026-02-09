<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">CI/CD Runners</h2>
        <p class="text-gray-500 mt-1 mb-0">GitHub Actions Runner Controller status and monitoring</p>
      </div>
      <button @click="loadAll" class="bg-[#42b983] text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors duration-300 hover:bg-[#35a372] disabled:bg-gray-300 disabled:cursor-not-allowed" :disabled="loading">
        <font-awesome-icon :icon="['fas', 'arrows-rotate']" :class="{ 'animate-spin': loading }" /> Refresh
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loading && !overview" class="bg-white p-12 rounded-lg shadow-md text-center text-gray-500">
      <div class="inline-block w-8 h-8 border-4 border-gray-200 border-t-[#42b983] rounded-full animate-spin mb-4"></div>
      <p class="m-0">Loading CI/CD runner status...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="bg-red-50 border-l-4 border-red-500 rounded-md p-6 mb-8">
      <strong class="block text-red-800 mb-2"><font-awesome-icon :icon="['fas', 'circle-xmark']" /> Failed to load CI/CD runner status</strong>
      <p class="m-0 text-red-700 text-sm">{{ error }}</p>
      <button @click="loadAll" class="mt-3 bg-red-600 text-white py-1.5 px-4 border-none rounded text-sm cursor-pointer hover:bg-red-700">Retry</button>
    </div>

    <!-- Empty state -->
    <div v-else-if="!loading && overview && !overview.runner_sets.length && !overview.controller.pods.length" class="bg-white p-12 rounded-lg shadow-md text-center">
      <font-awesome-icon :icon="['fas', 'code-branch']" class="text-5xl text-gray-300 mb-4" />
      <h3 class="text-lg font-semibold text-gray-700 mb-2">No ARC Runner Sets Found</h3>
      <p class="text-gray-500 text-sm m-0">Install the ARC controller and a runner set from the <router-link to="/modules/applications" class="text-blue-600 hover:underline">Modules</router-link> page.</p>
    </div>

    <template v-else-if="overview">
      <!-- Controller Health + Gauges -->
      <div class="bg-white p-6 rounded-lg shadow-md mb-6">
        <div class="grid grid-cols-4 gap-6">
          <!-- Controller Health -->
          <div class="flex flex-col items-center">
            <div class="relative w-[120px] h-[120px]">
              <svg viewBox="0 0 36 36" class="w-full h-full -rotate-90">
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e5e7eb" stroke-width="3" />
                <circle cx="18" cy="18" r="15.5" fill="none"
                  :stroke="overview.controller.healthy ? '#22c55e' : '#ef4444'" stroke-width="3" stroke-linecap="round"
                  :stroke-dasharray="overview.controller.healthy ? '97.4 97.4' : '0 97.4'" stroke-dashoffset="0" class="transition-all duration-700" />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <font-awesome-icon :icon="['fas', overview.controller.healthy ? 'check' : 'xmark']"
                  :class="overview.controller.healthy ? 'text-green-500' : 'text-red-500'" class="text-2xl" />
              </div>
            </div>
            <div class="mt-2 text-center">
              <div class="text-sm font-semibold text-gray-700">Controller</div>
              <div class="text-xs mt-0.5" :class="overview.controller.healthy ? 'text-green-500' : 'text-red-500'">
                {{ overview.controller.healthy ? 'Healthy' : 'Unhealthy' }}
              </div>
            </div>
          </div>

          <!-- Provisioned Gauge -->
          <div class="flex flex-col items-center">
            <div class="relative w-[120px] h-[120px]">
              <svg viewBox="0 0 36 36" class="w-full h-full -rotate-90">
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e5e7eb" stroke-width="3" />
                <circle cx="18" cy="18" r="15.5" fill="none"
                  :stroke="utilizationColor" stroke-width="3" stroke-linecap="round"
                  :stroke-dasharray="utilizationDash" stroke-dashoffset="0" class="transition-all duration-700" />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-2xl font-bold text-gray-900">{{ totalCurrent }}</span>
                <span class="text-[10px] text-gray-400 uppercase tracking-wide">pods</span>
              </div>
            </div>
            <div class="mt-2 text-center">
              <div class="text-sm font-semibold text-gray-700">Provisioned</div>
              <div class="text-xs text-gray-400 mt-0.5">{{ totalCurrent }} of {{ totalMax }} max</div>
            </div>
          </div>

          <!-- Executing Jobs Gauge -->
          <div class="flex flex-col items-center">
            <div class="relative w-[120px] h-[120px]">
              <svg viewBox="0 0 36 36" class="w-full h-full -rotate-90">
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e5e7eb" stroke-width="3" />
                <circle cx="18" cy="18" r="15.5" fill="none"
                  :stroke="totalBusy > 0 ? '#9333ea' : '#22c55e'" stroke-width="3" stroke-linecap="round"
                  :stroke-dasharray="busyDash" stroke-dashoffset="0" class="transition-all duration-700" />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-2xl font-bold text-gray-900">{{ totalBusy }}</span>
                <span class="text-[10px] text-gray-400 uppercase tracking-wide">jobs</span>
              </div>
            </div>
            <div class="mt-2 text-center">
              <div class="text-sm font-semibold text-gray-700">Executing Jobs</div>
              <div class="text-xs text-gray-400 mt-0.5">{{ totalIdle }} available, {{ totalCurrent }} total</div>
            </div>
          </div>

          <!-- Scale Sets Gauge -->
          <div class="flex flex-col items-center">
            <div class="relative w-[120px] h-[120px]">
              <svg viewBox="0 0 36 36" class="w-full h-full -rotate-90">
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e5e7eb" stroke-width="3" />
                <circle cx="18" cy="18" r="15.5" fill="none"
                  stroke="#6366f1" stroke-width="3" stroke-linecap="round"
                  :stroke-dasharray="scaleSetsDash" stroke-dashoffset="0" class="transition-all duration-700" />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-2xl font-bold text-gray-900">{{ overview.runner_sets.length }}</span>
                <span class="text-[10px] text-gray-400 uppercase tracking-wide">sets</span>
              </div>
            </div>
            <div class="mt-2 text-center">
              <div class="text-sm font-semibold text-gray-700">Scale Sets</div>
              <div class="text-xs text-gray-400 mt-0.5">{{ overview.runner_sets.length }} registered</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Runner Set Cards -->
      <div v-for="rs in overview.runner_sets" :key="rs.name + rs.namespace" class="bg-white rounded-lg shadow-md mb-6 overflow-hidden">
        <!-- Card Header -->
        <div class="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <font-awesome-icon :icon="['fas', 'code-branch']" class="text-indigo-500 text-lg" />
              <div>
                <h3 class="text-lg font-semibold text-gray-900 m-0">
                  <a v-if="rs.github_config_url" :href="rs.github_config_url" target="_blank" rel="noopener" class="text-gray-900 hover:text-blue-600 no-underline">
                    {{ extractGithubTarget(rs.github_config_url) }}
                    <font-awesome-icon :icon="['fas', 'arrow-up-right-from-square']" class="text-xs text-gray-400 ml-1" />
                  </a>
                  <span v-else>{{ rs.name }}</span>
                </h3>
                <div class="flex items-center gap-2 mt-1 text-xs text-gray-500">
                  <span>Release: <code class="bg-gray-200 px-1.5 py-0.5 rounded text-gray-600">{{ rs.name }}</code></span>
                  <span class="text-gray-300">|</span>
                  <span>Namespace: <code class="bg-gray-200 px-1.5 py-0.5 rounded text-gray-600">{{ rs.namespace }}</code></span>
                  <template v-if="rs.runner_group">
                    <span class="text-gray-300">|</span>
                    <span>Group: <span class="bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full font-medium">{{ rs.runner_group }}</span></span>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Stats Row -->
        <div class="px-6 py-4 grid grid-cols-5 gap-4 border-b border-gray-100">
          <div class="text-center" :title="`ARC scaling bounds: ${rs.min_runners} min, ${rs.max_runners} max`">
            <div class="text-2xl font-bold text-gray-900">{{ rs.min_runners }}<span class="text-gray-300 mx-1">/</span>{{ rs.max_runners }}</div>
            <div class="text-xs text-gray-400 uppercase tracking-wider mt-1">Scale Range</div>
          </div>
          <div class="text-center" :title="`${rs.current_runners} total runner pods created by ARC (${rs.running_runners} ready, ${rs.pending_runners} starting)`">
            <div class="text-2xl font-bold text-blue-600">{{ rs.current_runners }}</div>
            <div class="text-xs text-gray-400 uppercase tracking-wider mt-1">Provisioned</div>
            <div class="text-[10px] text-gray-400 mt-0.5">{{ rs.running_runners }} ready, {{ rs.pending_runners }} starting</div>
          </div>
          <div class="text-center" :title="`${busyCount(rs.name)} runners actively executing a GitHub Actions workflow job`">
            <div class="text-2xl font-bold text-purple-600">{{ busyCount(rs.name) }}</div>
            <div class="text-xs text-gray-400 uppercase tracking-wider mt-1">Executing Jobs</div>
          </div>
          <div class="text-center" :title="`${idleCount(rs.name)} runners registered with GitHub and waiting for a job`">
            <div class="text-2xl font-bold text-green-500">{{ idleCount(rs.name) }}</div>
            <div class="text-xs text-gray-400 uppercase tracking-wider mt-1">Available</div>
          </div>
          <div class="text-center" :title="`Runners not yet registered with GitHub (still initializing)`">
            <div class="text-2xl font-bold" :class="registeringCount(rs.name) > 0 ? 'text-amber-500' : 'text-gray-400'">{{ registeringCount(rs.name) }}</div>
            <div class="text-xs text-gray-400 uppercase tracking-wider mt-1">Registering</div>
          </div>
        </div>

        <!-- Runners Table -->
        <div class="px-6 py-4">
          <div v-if="!runners[rs.name] || !runners[rs.name].length" class="text-gray-400 text-center py-4 text-sm">
            No ephemeral runners active
          </div>
          <table v-else class="w-full border-collapse">
            <thead>
              <tr class="border-b border-gray-200">
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Runner</th>
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Pod Status</th>
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">GitHub Status</th>
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Age</th>
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Runner ID</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="runner in runners[rs.name]" :key="runner.name" class="border-b border-gray-50 hover:bg-gray-50">
                <td class="py-2.5 px-2 text-sm font-medium text-gray-900 font-mono">{{ runner.name }}</td>
                <td class="py-2.5 px-2">
                  <span :class="runnerStatusClass(runner.phase)" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ runner.phase }}</span>
                </td>
                <td class="py-2.5 px-2">
                  <div class="flex items-center gap-2">
                    <span v-if="runner.busy === true" class="bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full text-xs font-medium shrink-0">Executing Job</span>
                    <span v-else-if="runner.busy === false && runner.github_status === 'online'" class="bg-green-100 text-green-700 px-2 py-0.5 rounded-full text-xs font-medium shrink-0">Available</span>
                    <span v-else-if="runner.github_status === 'offline'" class="bg-red-100 text-red-700 px-2 py-0.5 rounded-full text-xs font-medium shrink-0">Offline</span>
                    <span v-else class="bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full text-xs font-medium shrink-0">Registering</span>
                    <span v-if="runner.job_display_name" class="text-xs text-gray-500 truncate" :title="runner.job_repository + ' / ' + runner.job_display_name">
                      {{ runner.job_repository ? runner.job_repository.split('/').pop() + ' / ' : '' }}{{ runner.job_display_name }}
                    </span>
                  </div>
                </td>
                <td class="py-2.5 px-2 text-sm text-gray-500">{{ formatAge(runner.age_seconds) }}</td>
                <td class="py-2.5 px-2 text-sm text-gray-500 font-mono">{{ runner.runner_id || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Listeners Section -->
      <div v-if="listeners.length" class="bg-white rounded-lg shadow-md mb-6 overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200 bg-gray-50 cursor-pointer flex items-center justify-between" @click="showListeners = !showListeners">
          <h3 class="text-sm font-semibold text-gray-700 m-0 uppercase tracking-wider">
            <font-awesome-icon :icon="['fas', showListeners ? 'chevron-down' : 'chevron-right']" class="mr-2 text-xs" />
            Listeners ({{ listeners.length }})
          </h3>
        </div>
        <div v-if="showListeners" class="px-6 py-4">
          <table class="w-full border-collapse">
            <thead>
              <tr class="border-b border-gray-200">
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Pod</th>
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Scale Set</th>
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Status</th>
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Ready</th>
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Restarts</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="l in listeners" :key="l.name" class="border-b border-gray-50 hover:bg-gray-50">
                <td class="py-2.5 px-2 text-sm font-mono text-gray-900">{{ l.name }}</td>
                <td class="py-2.5 px-2 text-sm text-gray-600">{{ l.scale_set_name }}</td>
                <td class="py-2.5 px-2">
                  <span :class="runnerStatusClass(l.status)" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ l.status }}</span>
                </td>
                <td class="py-2.5 px-2">
                  <span v-if="l.ready" class="text-green-500"><font-awesome-icon :icon="['fas', 'check']" /></span>
                  <span v-else class="text-gray-300"><font-awesome-icon :icon="['fas', 'xmark']" /></span>
                </td>
                <td class="py-2.5 px-2 text-sm" :class="l.restarts > 0 ? 'text-amber-500 font-medium' : 'text-gray-400'">{{ l.restarts }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Controller Pods (if unhealthy or for debugging) -->
      <div v-if="overview.controller.pods.length" class="bg-white rounded-lg shadow-md overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200 bg-gray-50 cursor-pointer flex items-center justify-between" @click="showControllerPods = !showControllerPods">
          <h3 class="text-sm font-semibold text-gray-700 m-0 uppercase tracking-wider">
            <font-awesome-icon :icon="['fas', showControllerPods ? 'chevron-down' : 'chevron-right']" class="mr-2 text-xs" />
            Controller Pods ({{ overview.controller.pods.length }})
          </h3>
        </div>
        <div v-if="showControllerPods" class="px-6 py-4">
          <table class="w-full border-collapse">
            <thead>
              <tr class="border-b border-gray-200">
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Pod</th>
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Status</th>
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Ready</th>
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Restarts</th>
                <th class="text-left py-2 px-2 text-gray-500 text-xs font-semibold uppercase tracking-wider">Age</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in overview.controller.pods" :key="p.name" class="border-b border-gray-50 hover:bg-gray-50">
                <td class="py-2.5 px-2 text-sm font-mono text-gray-900">{{ p.name }}</td>
                <td class="py-2.5 px-2">
                  <span :class="runnerStatusClass(p.status)" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ p.status }}</span>
                </td>
                <td class="py-2.5 px-2">
                  <span v-if="p.ready" class="text-green-500"><font-awesome-icon :icon="['fas', 'check']" /></span>
                  <span v-else class="text-gray-300"><font-awesome-icon :icon="['fas', 'xmark']" /></span>
                </td>
                <td class="py-2.5 px-2 text-sm" :class="p.restarts > 0 ? 'text-amber-500 font-medium' : 'text-gray-400'">{{ p.restarts }}</td>
                <td class="py-2.5 px-2 text-sm text-gray-500">{{ formatAge(p.age_seconds) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import apiService from '../services/api'
import websocketService from '../services/websocket'
import { useToast } from 'vue-toastification'

const CIRCUMFERENCE = 2 * Math.PI * 15.5  // ~97.4

export default {
  name: 'CiCdRunners',
  data() {
    return {
      loading: false,
      error: null,
      overview: null,
      runners: {},
      listeners: [],
      unsubscribeWs: null,
      showListeners: false,
      showControllerPods: false,
    }
  },
  computed: {
    totalMax() {
      if (!this.overview) return 0
      return this.overview.runner_sets.reduce((s, rs) => s + (rs.max_runners || 0), 0)
    },
    totalRunning() {
      if (!this.overview) return 0
      return this.overview.runner_sets.reduce((s, rs) => s + (rs.running_runners || 0), 0)
    },
    totalPending() {
      if (!this.overview) return 0
      return this.overview.runner_sets.reduce((s, rs) => s + (rs.pending_runners || 0), 0)
    },
    totalCurrent() {
      if (!this.overview) return 0
      return this.overview.runner_sets.reduce((s, rs) => s + (rs.current_runners || 0), 0)
    },
    utilizationPercent() {
      if (this.totalMax === 0) return 0
      return Math.round((this.totalCurrent / this.totalMax) * 100)
    },
    utilizationColor() {
      const pct = this.utilizationPercent
      if (pct >= 90) return '#ef4444'
      if (pct >= 70) return '#f59e0b'
      return '#22c55e'
    },
    utilizationDash() {
      const pct = this.totalMax > 0 ? this.totalCurrent / this.totalMax : 0
      const filled = pct * CIRCUMFERENCE
      return `${filled} ${CIRCUMFERENCE}`
    },
    allRunners() {
      return Object.values(this.runners).flat()
    },
    totalBusy() {
      return this.allRunners.filter(r => r.busy === true).length
    },
    totalIdle() {
      return this.allRunners.filter(r => r.busy === false && r.github_status === 'online').length
    },
    busyDash() {
      const total = Math.max(this.allRunners.length, 1)
      const pct = this.totalBusy / total
      const filled = Math.min(pct, 1) * CIRCUMFERENCE
      return `${filled} ${CIRCUMFERENCE}`
    },
    scaleSetsDash() {
      const count = this.overview?.runner_sets?.length || 0
      // Show full ring if any sets exist
      const filled = count > 0 ? CIRCUMFERENCE : 0
      return `${filled} ${CIRCUMFERENCE}`
    },
  },
  async mounted() {
    this.toast = useToast()
    await this.loadAll()
    // Subscribe to server-pushed cicd_update broadcasts (every ~10s)
    this.unsubscribeWs = websocketService.subscribe((event) => {
      if (event.type === 'cicd_update' && event.data) {
        this.applySnapshot(event.data)
      } else if (event.type === 'module_status_changed') {
        this.loadAll()
      }
    })
  },
  beforeUnmount() {
    this.unsubscribeWs?.()
  },
  methods: {
    applySnapshot(data) {
      this.overview = data.overview
      this.listeners = data.listeners || []
      const runnersMap = {}
      for (const r of (data.runners || [])) {
        const key = r.scale_set_name || ''
        if (!runnersMap[key]) runnersMap[key] = []
        runnersMap[key].push(r)
      }
      this.runners = runnersMap
      this.error = null
    },
    async loadAll() {
      this.loading = true
      this.error = null
      try {
        const data = await apiService.cicdFull()
        this.applySnapshot(data)
      } catch (e) {
        this.error = e?.message || 'Failed to load CI/CD runner status'
      } finally {
        this.loading = false
      }
    },
    busyCount(scaleSetName) {
      return (this.runners[scaleSetName] || []).filter(r => r.busy === true).length
    },
    idleCount(scaleSetName) {
      return (this.runners[scaleSetName] || []).filter(r => r.busy === false && r.github_status === 'online').length
    },
    registeringCount(scaleSetName) {
      return (this.runners[scaleSetName] || []).filter(r => r.busy === null && r.github_status !== 'online').length
    },
    runnerStatusClass(status) {
      switch (status) {
        case 'Running': return 'bg-green-100 text-green-700'
        case 'Pending': return 'bg-amber-100 text-amber-700'
        case 'Succeeded': return 'bg-blue-100 text-blue-700'
        case 'Failed': return 'bg-red-100 text-red-700'
        default: return 'bg-gray-100 text-gray-600'
      }
    },
    extractGithubTarget(url) {
      if (!url) return ''
      try {
        const parts = new URL(url).pathname.split('/').filter(Boolean)
        return parts.join('/')
      } catch {
        return url
      }
    },
    formatAge(seconds) {
      if (!seconds || seconds <= 0) return '—'
      if (seconds < 60) return `${seconds}s`
      if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
      if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
      return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`
    },
  },
}
</script>
