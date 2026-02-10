<template>
  <div :class="fullscreen ? 'fixed inset-0 z-[9998] bg-[var(--th-bg-page,#f3f4f6)]' : ''">
    <!-- Header -->
    <div v-if="!fullscreen" class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0" style="color: var(--th-text-heading, #111827);">Workload Graph</h2>
        <p class="text-gray-500 mt-1 mb-0" style="color: var(--th-text-muted, #6b7280);">Visualize Kubernetes workload relationships and drill into resource stacks</p>
      </div>
      <button @click="loadWorkloadData" :disabled="loading"
        class="bg-blue-600 text-white py-2.5 px-5 rounded border-none cursor-pointer text-[0.9rem] font-medium transition-colors hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50">
        <font-awesome-icon :icon="['fas', 'arrows-rotate']" :class="{ 'animate-spin': loading }" /> Refresh
      </button>
    </div>

    <!-- Namespace selector + controls -->
    <div class="flex items-center gap-4" :class="fullscreen ? 'px-4 py-3' : 'mb-6'">
      <div class="flex items-center gap-2">
        <label class="font-medium text-gray-700 whitespace-nowrap text-sm" style="color: var(--th-text, #374151);">Namespace:</label>
        <select v-model="selectedNamespace" class="p-2 border border-gray-300 rounded text-sm"
          style="background-color: var(--th-bg-card, #fff); border-color: var(--th-border, #d1d5db); color: var(--th-text, #374151);">
          <option value="" disabled>Select a namespace...</option>
          <option v-for="ns in namespaces" :key="ns" :value="ns">{{ ns }}</option>
        </select>
      </div>
      <div class="flex items-center gap-2 ml-auto">
        <label class="flex items-center gap-1.5 text-sm cursor-pointer" style="color: var(--th-text-secondary, #6b7280);">
          <input type="checkbox" v-model="showSystem" class="cursor-pointer" />
          Show system resources
        </label>
        <button v-if="fullscreen" @click="loadWorkloadData" :disabled="loading"
          class="bg-blue-600 text-white py-1.5 px-3 rounded border-none cursor-pointer text-sm font-medium transition-colors hover:bg-blue-700 flex items-center gap-1.5 disabled:opacity-50 ml-2">
          <font-awesome-icon :icon="['fas', 'arrows-rotate']" :class="{ 'animate-spin': loading }" /> Refresh
        </button>
        <button @click="toggleFullscreen"
          class="w-8 h-8 flex items-center justify-center rounded border cursor-pointer text-sm transition-colors ml-2"
          style="background-color: var(--th-bg-card, #fff); border-color: var(--th-border, #e5e7eb); color: var(--th-text-secondary, #6b7280);"
          :title="fullscreen ? 'Exit fullscreen' : 'Fullscreen'">
          <font-awesome-icon :icon="['fas', fullscreen ? 'compress' : 'expand']" />
        </button>
      </div>
    </div>

    <!-- Side-by-side layout: list left, graph right -->
    <div v-if="!fullscreen" class="flex gap-6 items-start">

      <!-- Left: List content -->
      <div class="w-2/5 min-w-0 rounded-lg shadow-sm p-5 overflow-y-auto"
        style="max-height: calc(100vh - 220px); background-color: var(--th-bg-card, #fff);">
        <!-- Tabs -->
        <div class="flex border-b mb-6 gap-1" style="border-color: var(--th-border-light, #e5e7eb);">
          <button v-for="t in tabs" :key="t.key" @click="activeTab = t.key"
            class="py-2.5 px-4 text-sm font-medium border-b-2 transition-colors cursor-pointer bg-transparent"
            :class="activeTab === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'">
            {{ t.label }}
            <span v-if="tabCounts[t.key] !== undefined" class="ml-1 text-xs text-gray-400">({{ tabCounts[t.key] }})</span>
          </button>
        </div>

        <!-- Loading -->
        <div v-if="loading" class="text-center py-12" style="color: var(--th-text-muted, #6b7280);">Loading...</div>

        <!-- Empty state -->
        <div v-else-if="currentItems.length === 0" class="text-center py-12">
          <p class="text-gray-500 text-sm">No resources found.</p>
        </div>

        <!-- Resource list -->
        <div v-else class="space-y-2">
          <template v-for="item in currentItems" :key="item.id">
            <!-- Section header -->
            <div v-if="item.isHeader"
              class="text-xs font-semibold uppercase tracking-wider pt-3 pb-1 px-1 first:pt-0"
              style="color: var(--th-text-muted, #9ca3af);">
              {{ item.headerLabel }}
            </div>
            <!-- Resource item -->
            <div v-else
              @click="focusNode(item.id)"
              class="p-3 rounded-lg border cursor-pointer transition-all hover:shadow-sm"
              :class="{
                'ring-2 ring-blue-500': focusedNodeId === item.id,
                'bg-blue-50 border-blue-200': focusedNodeId !== item.id && relatedNodeIds.has(item.id),
              }"
              :style="focusedNodeId !== item.id && !relatedNodeIds.has(item.id) ? `background-color: var(--th-bg-card-alt, #f9fafb); border-color: var(--th-border-light, #e5e7eb);` : ''">
              <div class="flex items-center gap-3">
                <span class="w-3 h-3 rounded-sm shrink-0 inline-block" :style="{ backgroundColor: item.color }"></span>
                <div class="min-w-0 flex-1">
                  <div class="font-medium text-sm truncate" style="color: var(--th-text, #374151);">{{ item.name }}</div>
                  <div class="text-xs truncate" style="color: var(--th-text-muted, #9ca3af);">
                    {{ item.namespace }}
                    <span v-if="item.status" class="ml-2">{{ item.status }}</span>
                  </div>
                </div>
                <span v-if="item.badge" class="px-2 py-0.5 rounded text-xs font-medium shrink-0" :class="item.badgeClass">
                  {{ item.badge }}
                </span>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Right: Graph -->
      <div class="w-3/5 sticky top-20">
        <WorkloadGraph
          ref="graph"
          :workload-data="workloadData"
          :focus-node-id="focusedNodeId"
          :fullscreen="false"
          @node-selected="onGraphNodeSelected"
          @related-nodes="onRelatedNodes"
        />
      </div>
    </div>

    <!-- Fullscreen graph -->
    <div v-if="fullscreen" class="flex-1" style="height: calc(100vh - 52px);">
      <WorkloadGraph
        ref="graph"
        :workload-data="workloadData"
        :focus-node-id="focusedNodeId"
        :fullscreen="true"
        @node-selected="onGraphNodeSelected"
        @related-nodes="onRelatedNodes"
      />
    </div>
  </div>
</template>

<script>
import WorkloadGraph from './WorkloadGraph.vue'
import apiService from '../services/api'

const TAB_COLORS = {
  deployment:  '#3b82f6',
  statefulset: '#8b5cf6',
  daemonset:   '#6366f1',
  pod:         '#22c55e',
  service:     '#f59e0b',
  ingress:     '#f97316',
  configmap:   '#06b6d4',
  secret:      '#ef4444',
  pvc:         '#a855f7',
}

export default {
  name: 'WorkloadManagement',
  components: { WorkloadGraph },

  data() {
    return {
      loading: false,
      activeTab: 'controllers',
      selectedNamespace: '',
      showSystem: false,
      namespaces: [],
      workloadData: {},
      focusedNodeId: null,
      relatedNodeIds: new Set(),
      fullscreen: false,
    }
  },

  computed: {
    tabs() {
      return [
        { key: 'controllers', label: 'Controllers' },
        { key: 'pods', label: 'Pods' },
        { key: 'networking', label: 'Networking' },
        { key: 'config', label: 'Config' },
        { key: 'storage', label: 'Storage' },
      ]
    },

    tabCounts() {
      const d = this.workloadData
      return {
        controllers: (d.deployments?.length || 0) + (d.statefulsets?.length || 0) + (d.daemonsets?.length || 0),
        pods: d.pods?.length || 0,
        networking: (d.services?.length || 0) + (d.ingresses?.length || 0),
        config: (d.configmaps?.length || 0) + (d.secrets?.length || 0),
        storage: d.pvcs?.length || 0,
      }
    },

    currentItems() {
      const d = this.workloadData
      switch (this.activeTab) {
        case 'controllers': {
          const groups = [
            { type: 'DaemonSet', items: (d.daemonsets || []).map(r => ({
              id: `ds:${r.namespace}/${r.name}`, name: r.name, namespace: r.namespace,
              color: TAB_COLORS.daemonset, type: 'DaemonSet',
              badge: `${r.ready || 0}/${r.desired || 0}`,
              badgeClass: (r.ready || 0) === (r.desired || 0) ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700',
              status: 'DaemonSet',
            }))},
            { type: 'Deployment', items: (d.deployments || []).map(r => ({
              id: `deploy:${r.namespace}/${r.name}`, name: r.name, namespace: r.namespace,
              color: TAB_COLORS.deployment, type: 'Deployment',
              badge: `${r.ready_replicas || 0}/${r.replicas || 0}`,
              badgeClass: (r.ready_replicas || 0) === (r.replicas || 0) ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700',
              status: 'Deployment',
            }))},
            { type: 'StatefulSet', items: (d.statefulsets || []).map(r => ({
              id: `sts:${r.namespace}/${r.name}`, name: r.name, namespace: r.namespace,
              color: TAB_COLORS.statefulset, type: 'StatefulSet',
              badge: `${r.ready_replicas || 0}/${r.replicas || 0}`,
              badgeClass: (r.ready_replicas || 0) === (r.replicas || 0) ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700',
              status: 'StatefulSet',
            }))},
          ]
          const result = []
          for (const g of groups) {
            const sorted = g.items.sort((a, b) => a.name.localeCompare(b.name))
            if (sorted.length > 0) {
              result.push({ id: `header:${g.type}`, isHeader: true, headerLabel: `${g.type}s (${sorted.length})` })
              result.push(...sorted)
            }
          }
          return result
        }
        case 'pods':
          return (d.pods || []).map(r => ({
            id: `pod:${r.namespace}/${r.name}`, name: r.name, namespace: r.namespace,
            color: TAB_COLORS.pod, type: 'Pod',
            badge: r.phase,
            badgeClass: r.phase === 'Running' ? 'bg-green-100 text-green-700'
              : r.phase === 'Pending' ? 'bg-yellow-100 text-yellow-700'
              : r.phase === 'Failed' ? 'bg-red-100 text-red-700'
              : 'bg-gray-100 text-gray-700',
            status: null,
          }))
        case 'networking':
          return [
            ...(d.services || []).map(r => ({
              id: `svc:${r.namespace}/${r.name}`, name: r.name, namespace: r.namespace,
              color: TAB_COLORS.service, type: 'Service',
              badge: r.type,
              badgeClass: 'bg-amber-100 text-amber-700',
              status: 'Service',
            })),
            ...(d.ingresses || []).map(r => ({
              id: `ing:${r.namespace}/${r.name}`, name: r.name, namespace: r.namespace,
              color: TAB_COLORS.ingress, type: 'Ingress',
              badge: null, badgeClass: '',
              status: 'Ingress',
            })),
          ]
        case 'config':
          return [
            ...(d.configmaps || []).map(r => ({
              id: `cm:${r.namespace}/${r.name}`, name: r.name, namespace: r.namespace,
              color: TAB_COLORS.configmap, type: 'ConfigMap',
              badge: `${r.data_keys?.length || 0} keys`,
              badgeClass: 'bg-cyan-100 text-cyan-700',
              status: 'ConfigMap',
            })),
            ...(d.secrets || []).map(r => ({
              id: `sec:${r.namespace}/${r.name}`, name: r.name, namespace: r.namespace,
              color: TAB_COLORS.secret, type: 'Secret',
              badge: r.type === 'Opaque' ? null : r.type,
              badgeClass: 'bg-red-100 text-red-700',
              status: 'Secret',
            })),
          ]
        case 'storage':
          return (d.pvcs || []).map(r => ({
            id: `pvc:${r.namespace}/${r.name}`, name: r.name, namespace: r.namespace,
            color: TAB_COLORS.pvc, type: 'PVC',
            badge: r.capacity || r.phase,
            badgeClass: r.phase === 'Bound' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700',
            status: r.storage_class ? `SC: ${r.storage_class}` : null,
          }))
        default:
          return []
      }
    },
  },

  watch: {
    selectedNamespace() { if (this.selectedNamespace) this.loadWorkloadData() },
    showSystem() { this.fetchNamespaces(); if (this.selectedNamespace) this.loadWorkloadData() },
  },

  mounted() {
    this.fetchNamespaces()
  },

  methods: {
    async fetchNamespaces() {
      try {
        const data = await apiService.workloadsList({ include_system: this.showSystem })
        const allNs = data.namespaces || []
        if (this.showSystem) {
          this.namespaces = allNs
        } else {
          const systemNs = new Set(['kube-system', 'kube-public', 'kube-node-lease'])
          this.namespaces = allNs.filter(ns => !systemNs.has(ns))
        }
      } catch (error) {
        console.error('Failed to fetch namespaces:', error)
      }
    },

    async loadWorkloadData() {
      if (!this.selectedNamespace) return
      this.loading = true
      try {
        const params = { include_system: this.showSystem, namespace: this.selectedNamespace }
        this.workloadData = await apiService.workloadsList(params)
      } catch (error) {
        console.error('Failed to load workload data:', error)
      } finally {
        this.loading = false
      }
    },

    focusNode(nodeId) {
      this.focusedNodeId = nodeId
    },

    onGraphNodeSelected(nodeId) {
      this.focusedNodeId = nodeId
    },

    onRelatedNodes(ids) {
      this.relatedNodeIds = ids
    },

    toggleFullscreen() {
      this.fullscreen = !this.fullscreen
      this.$nextTick(() => {
        if (this.$refs.graph && this.$refs.graph.cy) {
          this.$refs.graph.cy.resize()
          this.$refs.graph.fitGraph()
        }
      })
    },
  },
}
</script>
