<template>
  <div class="relative h-full" ref="wrapper">
    <!-- Toolbar -->
    <div class="absolute top-3 right-3 z-10 flex gap-1.5">
      <button @click="fitGraph" title="Fit to view"
        class="w-8 h-8 flex items-center justify-center rounded bg-white/90 border border-gray-200 text-gray-600 hover:bg-gray-100 cursor-pointer text-sm shadow-sm"
        style="background-color: var(--th-bg-card, #fff); border-color: var(--th-border, #e5e7eb); color: var(--th-text-secondary, #6b7280);">
        <font-awesome-icon :icon="['fas', 'arrows-rotate']" />
      </button>
      <select v-model="layoutName" @change="runLayout" title="Layout algorithm"
        class="h-8 pl-2 pr-6 rounded border text-xs cursor-pointer shadow-sm appearance-none"
        style="background-color: var(--th-bg-card, #fff); border-color: var(--th-border, #e5e7eb); color: var(--th-text-secondary, #6b7280);">
        <option value="fcose">Clustered</option>
        <option value="dagre">Hierarchical</option>
        <option value="cose">Force-directed</option>
        <option value="concentric">Concentric</option>
        <option value="breadthfirst">Tree</option>
        <option value="circle">Circle</option>
      </select>
    </div>

    <!-- Legend -->
    <div class="absolute bottom-3 left-3 z-10 rounded-lg p-3 shadow-sm border text-xs space-y-1"
      style="background-color: var(--th-bg-card, #fff); border-color: var(--th-border, #e5e7eb); color: var(--th-text, #374151);">
      <div class="font-medium mb-1" style="color: var(--th-text-heading, #2c3e50);">Legend</div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-sm inline-block" style="background:#3b82f6"></span> Deployment</div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-sm inline-block" style="background:#8b5cf6"></span> StatefulSet</div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-sm inline-block" style="background:#6366f1"></span> DaemonSet</div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-sm inline-block" style="background:#22c55e"></span> Pod</div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-sm inline-block" style="background:#f59e0b"></span> Service</div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-sm inline-block" style="background:#f97316"></span> Ingress</div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-sm inline-block" style="background:#06b6d4"></span> ConfigMap</div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-sm inline-block" style="background:#ef4444"></span> Secret</div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-sm inline-block" style="background:#a855f7"></span> PVC</div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full inline-block" style="background:#1e40af"></span> Internet</div>
      <hr class="border-gray-200 my-1" style="border-color: var(--th-border-light, #f3f4f6);">
      <div class="flex items-center gap-2"><span class="w-4 border-t-2 border-gray-500 inline-block"></span> owns</div>
      <div class="flex items-center gap-2"><span class="w-4 border-t-2 border-dashed inline-block" style="border-color:#f97316"></span> selects</div>
      <div class="flex items-center gap-2"><span class="w-4 border-t-2 border-dashed inline-block" style="border-color:#f97316"></span> routes</div>
      <div class="flex items-center gap-2"><span class="w-4 border-t-2 border-dashed inline-block" style="border-color:#06b6d4"></span> mounts</div>
      <div class="flex items-center gap-2"><span class="w-4 border-t-2 border-dashed inline-block" style="border-color:#f97316"></span> external</div>
    </div>

    <!-- Cytoscape container -->
    <div ref="cyContainer" class="w-full rounded-lg border"
      :style="{ height: fullscreen ? '100%' : 'calc(100vh - 220px)', backgroundColor: 'var(--th-bg-card-alt, #f9fafb)', borderColor: 'var(--th-border, #e5e7eb)' }"></div>

    <!-- Layout computing overlay -->
    <div v-if="layoutRunning" class="absolute inset-0 flex items-center justify-center rounded-lg z-20"
      style="background-color: var(--th-bg-card-alt, #f9fafb); backdrop-filter: blur(2px);">
      <div class="flex flex-col items-center gap-3">
        <div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <span class="text-sm font-medium" style="color: var(--th-text-secondary, #6b7280);">Computing layout...</span>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="isEmpty" class="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div class="text-center">
        <p class="text-gray-400 text-sm">No workload resources to display.</p>
        <p class="text-gray-300 text-xs mt-1">Select a namespace or enable system resources.</p>
      </div>
    </div>

    <!-- Detail panel -->
    <div v-if="selected" class="absolute top-0 right-0 w-72 h-full rounded-r-lg border-l overflow-y-auto shadow-lg"
      style="background-color: var(--th-bg-card, #fff); border-color: var(--th-border, #e5e7eb);">
      <div class="p-4">
        <div class="flex items-center justify-between mb-3">
          <span class="px-2 py-0.5 rounded text-xs font-medium" :class="selectedBadgeClass">{{ selectedTypeLabel }}</span>
          <button @click="clearSelection" class="text-gray-400 hover:text-gray-600 bg-transparent border-none cursor-pointer"
            style="color: var(--th-text-muted, #9ca3af);">
            <font-awesome-icon :icon="['fas', 'xmark']" />
          </button>
        </div>
        <h4 class="text-lg font-semibold m-0 mb-1" style="color: var(--th-text-heading, #2c3e50);">{{ selected.label }}</h4>
        <p v-if="selected.namespace" class="text-xs m-0 mb-4" style="color: var(--th-text-muted, #9ca3af);">Namespace: {{ selected.namespace }}</p>

        <!-- Deployment / StatefulSet details -->
        <div v-if="selected.nodeType === 'deployment' || selected.nodeType === 'statefulset'">
          <div class="flex items-center gap-2 mb-3">
            <span class="text-sm font-medium" style="color: var(--th-text, #374151);">Replicas:</span>
            <span class="px-2 py-0.5 rounded text-xs font-medium"
              :class="selected.readyReplicas === selected.replicas ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'">
              {{ selected.readyReplicas || 0 }}/{{ selected.replicas || 0 }}
            </span>
          </div>
          <h5 class="text-sm font-medium mb-2" style="color: var(--th-text, #374151);">Connected Resources</h5>
          <div v-for="edge in selectedEdges" :key="edge.id" class="text-sm py-1.5 border-b"
            style="border-color: var(--th-border-light, #f3f4f6); color: var(--th-text, #374151);">
            <div class="font-medium">{{ edge.targetLabel }}</div>
            <div class="text-xs" style="color: var(--th-text-muted, #9ca3af);">{{ edge.edgeType }} {{ edge.direction === 'out' ? '→' : '←' }}</div>
          </div>
          <div v-if="selectedEdges.length === 0" class="text-xs italic" style="color: var(--th-text-muted, #9ca3af);">No connections</div>
        </div>

        <!-- DaemonSet details -->
        <div v-else-if="selected.nodeType === 'daemonset'">
          <div class="flex items-center gap-2 mb-3">
            <span class="text-sm font-medium" style="color: var(--th-text, #374151);">Nodes:</span>
            <span class="px-2 py-0.5 rounded text-xs font-medium"
              :class="selected.ready === selected.desired ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'">
              {{ selected.ready || 0 }}/{{ selected.desired || 0 }}
            </span>
          </div>
          <h5 class="text-sm font-medium mb-2" style="color: var(--th-text, #374151);">Connected Resources</h5>
          <div v-for="edge in selectedEdges" :key="edge.id" class="text-sm py-1.5 border-b"
            style="border-color: var(--th-border-light, #f3f4f6); color: var(--th-text, #374151);">
            <div class="font-medium">{{ edge.targetLabel }}</div>
            <div class="text-xs" style="color: var(--th-text-muted, #9ca3af);">{{ edge.edgeType }} {{ edge.direction === 'out' ? '→' : '←' }}</div>
          </div>
        </div>

        <!-- Pod details -->
        <div v-else-if="selected.nodeType === 'pod'">
          <div class="flex items-center gap-2 mb-3">
            <span class="text-sm font-medium" style="color: var(--th-text, #374151);">Phase:</span>
            <span class="px-2 py-0.5 rounded text-xs font-medium" :class="podPhaseClass(selected.phase)">
              {{ selected.phase }}
            </span>
          </div>
          <div v-if="selected.raw && selected.raw.service_account_name" class="text-xs mb-3" style="color: var(--th-text-muted, #9ca3af);">
            SA: {{ selected.raw.service_account_name }}
          </div>
          <h5 class="text-sm font-medium mb-2" style="color: var(--th-text, #374151);">Connected Resources</h5>
          <div v-for="edge in selectedEdges" :key="edge.id" class="text-sm py-1.5 border-b"
            style="border-color: var(--th-border-light, #f3f4f6); color: var(--th-text, #374151);">
            <div class="font-medium">{{ edge.targetLabel }}</div>
            <div class="text-xs" style="color: var(--th-text-muted, #9ca3af);">{{ edge.edgeType }} {{ edge.direction === 'out' ? '→' : '←' }}</div>
          </div>
          <div v-if="selectedEdges.length === 0" class="text-xs italic" style="color: var(--th-text-muted, #9ca3af);">No connections</div>
        </div>

        <!-- Service details -->
        <div v-else-if="selected.nodeType === 'service'">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-sm font-medium" style="color: var(--th-text, #374151);">Type:</span>
            <span class="text-xs" style="color: var(--th-text-muted, #9ca3af);">{{ selected.serviceType || 'ClusterIP' }}</span>
          </div>
          <div v-if="selected.ports && selected.ports.length" class="mb-3">
            <span class="text-xs font-medium" style="color: var(--th-text, #374151);">Ports:</span>
            <div v-for="p in selected.ports" :key="p.port" class="text-xs ml-2" style="color: var(--th-text-muted, #9ca3af);">
              {{ p.name ? p.name + ': ' : '' }}{{ p.port }}{{ p.target_port ? ' → ' + p.target_port : '' }}/{{ p.protocol }}
            </div>
          </div>
          <h5 class="text-sm font-medium mb-2" style="color: var(--th-text, #374151);">Connected Resources</h5>
          <div v-for="edge in selectedEdges" :key="edge.id" class="text-sm py-1.5 border-b"
            style="border-color: var(--th-border-light, #f3f4f6); color: var(--th-text, #374151);">
            <div class="font-medium">{{ edge.targetLabel }}</div>
            <div class="text-xs" style="color: var(--th-text-muted, #9ca3af);">{{ edge.edgeType }} {{ edge.direction === 'out' ? '→' : '←' }}</div>
          </div>
        </div>

        <!-- Ingress details -->
        <div v-else-if="selected.nodeType === 'ingress'">
          <div v-if="selected.raw && selected.raw.backends && selected.raw.backends.length" class="mb-3">
            <span class="text-xs font-medium" style="color: var(--th-text, #374151);">Rules:</span>
            <div v-for="(b, i) in selected.raw.backends" :key="i" class="text-xs ml-2 py-1" style="color: var(--th-text-muted, #9ca3af);">
              {{ b.host }}{{ b.path }} → {{ b.service_name }}:{{ b.service_port }}
            </div>
          </div>
          <h5 class="text-sm font-medium mb-2" style="color: var(--th-text, #374151);">Connected Resources</h5>
          <div v-for="edge in selectedEdges" :key="edge.id" class="text-sm py-1.5 border-b"
            style="border-color: var(--th-border-light, #f3f4f6); color: var(--th-text, #374151);">
            <div class="font-medium">{{ edge.targetLabel }}</div>
            <div class="text-xs" style="color: var(--th-text-muted, #9ca3af);">{{ edge.edgeType }}</div>
          </div>
        </div>

        <!-- ConfigMap / Secret details -->
        <div v-else-if="selected.nodeType === 'configmap' || selected.nodeType === 'secret'">
          <div v-if="selected.nodeType === 'secret' && selected.secretType" class="text-xs mb-2" style="color: var(--th-text-muted, #9ca3af);">
            Type: {{ selected.secretType }}
          </div>
          <div v-if="selected.dataKeys && selected.dataKeys.length" class="mb-3">
            <span class="text-xs font-medium" style="color: var(--th-text, #374151);">Keys:</span>
            <div v-for="key in selected.dataKeys" :key="key" class="text-xs ml-2" style="color: var(--th-text-muted, #9ca3af);">{{ key }}</div>
          </div>
          <h5 class="text-sm font-medium mb-2" style="color: var(--th-text, #374151);">Referenced By</h5>
          <div v-for="edge in selectedEdges" :key="edge.id" class="text-sm py-1.5 border-b"
            style="border-color: var(--th-border-light, #f3f4f6); color: var(--th-text, #374151);">
            <div class="font-medium">{{ edge.targetLabel }}</div>
            <div class="text-xs" style="color: var(--th-text-muted, #9ca3af);">{{ edge.edgeType }}</div>
          </div>
          <div v-if="selectedEdges.length === 0" class="text-xs italic" style="color: var(--th-text-muted, #9ca3af);">Not referenced by any pod</div>
        </div>

        <!-- PVC details -->
        <div v-else-if="selected.nodeType === 'pvc'">
          <div class="space-y-1 mb-3 text-xs" style="color: var(--th-text-muted, #9ca3af);">
            <div v-if="selected.capacity">Capacity: {{ selected.capacity }}</div>
            <div v-if="selected.storageClass">Storage Class: {{ selected.storageClass }}</div>
            <div v-if="selected.pvcPhase">Status: {{ selected.pvcPhase }}</div>
          </div>
          <h5 class="text-sm font-medium mb-2" style="color: var(--th-text, #374151);">Referenced By</h5>
          <div v-for="edge in selectedEdges" :key="edge.id" class="text-sm py-1.5 border-b"
            style="border-color: var(--th-border-light, #f3f4f6); color: var(--th-text, #374151);">
            <div class="font-medium">{{ edge.targetLabel }}</div>
          </div>
          <div v-if="selectedEdges.length === 0" class="text-xs italic" style="color: var(--th-text-muted, #9ca3af);">Not mounted by any pod</div>
        </div>

        <!-- Namespace details -->
        <div v-else-if="selected.nodeType === 'namespace'">
          <h5 class="text-sm font-medium mb-2" style="color: var(--th-text, #374151);">Resources</h5>
          <div class="space-y-1 text-xs" style="color: var(--th-text-muted, #9ca3af);">
            <div v-for="(count, type) in namespaceCounts" :key="type">{{ count }} {{ type }}</div>
          </div>
        </div>

        <!-- Generic fallback (replicaset, serviceaccount) -->
        <div v-else>
          <h5 class="text-sm font-medium mb-2" style="color: var(--th-text, #374151);">Connected Resources</h5>
          <div v-for="edge in selectedEdges" :key="edge.id" class="text-sm py-1.5 border-b"
            style="border-color: var(--th-border-light, #f3f4f6); color: var(--th-text, #374151);">
            <div class="font-medium">{{ edge.targetLabel }}</div>
            <div class="text-xs" style="color: var(--th-text-muted, #9ca3af);">{{ edge.edgeType }} {{ edge.direction === 'out' ? '→' : '←' }}</div>
          </div>
          <div v-if="selectedEdges.length === 0" class="text-xs italic" style="color: var(--th-text-muted, #9ca3af);">No connections</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import fcose from 'cytoscape-fcose'
import { buildWorkloadElements } from '../services/workloadGraphBuilder'

cytoscape.use(dagre)
cytoscape.use(fcose)

const NODE_COLORS = {
  deployment:     { bg: '#3b82f6', border: '#2563eb', text: '#ffffff' },
  statefulset:    { bg: '#8b5cf6', border: '#7c3aed', text: '#ffffff' },
  daemonset:      { bg: '#6366f1', border: '#4f46e5', text: '#ffffff' },
  replicaset:     { bg: '#60a5fa', border: '#3b82f6', text: '#ffffff' },
  pod:            { bg: '#22c55e', border: '#16a34a', text: '#ffffff' },
  service:        { bg: '#f59e0b', border: '#d97706', text: '#ffffff' },
  ingress:        { bg: '#f97316', border: '#ea580c', text: '#ffffff' },
  configmap:      { bg: '#06b6d4', border: '#0891b2', text: '#ffffff' },
  secret:         { bg: '#ef4444', border: '#dc2626', text: '#ffffff' },
  pvc:            { bg: '#a855f7', border: '#9333ea', text: '#ffffff' },
  serviceaccount: { bg: '#14b8a6', border: '#0d9488', text: '#ffffff' },
  internet:       { bg: '#1e40af', border: '#1e3a8a', text: '#ffffff' },
  namespace:      { bg: '#e5e7eb', border: '#9ca3af', text: '#374151' },
  zone:           { bg: '#dbeafe', border: '#93c5fd', text: '#1e40af' },
}

const NODE_SHAPES = {
  deployment:     'round-rectangle',
  statefulset:    'rectangle',
  daemonset:      'hexagon',
  replicaset:     'round-rectangle',
  pod:            'ellipse',
  service:        'diamond',
  ingress:        'triangle',
  configmap:      'barrel',
  secret:         'octagon',
  pvc:            'rectangle',
  serviceaccount: 'round-rectangle',
  internet:       'ellipse',
  namespace:      'round-rectangle',
  zone:           'round-rectangle',
}

const NODE_SIZES = {
  deployment: 45, statefulset: 45, daemonset: 45,
  replicaset: 35,
  pod: 30,
  service: 40, ingress: 40,
  configmap: 30, secret: 30, pvc: 30, serviceaccount: 30,
  internet: 50,
}

const EDGE_COLORS = {
  owns:     '#6b7280',
  selects:  '#f97316',
  routes:   '#f97316',
  mounts:   '#06b6d4',
  usessa:   '#14b8a6',
  external: '#f97316',
}

const POD_PHASE_COLORS = {
  Running:   { bg: '#22c55e', border: '#16a34a' },
  Pending:   { bg: '#eab308', border: '#ca8a04' },
  Succeeded: { bg: '#3b82f6', border: '#2563eb' },
  Failed:    { bg: '#ef4444', border: '#dc2626' },
  Unknown:   { bg: '#9ca3af', border: '#6b7280' },
}

const TYPE_LABELS = {
  deployment: 'Deployment', statefulset: 'StatefulSet', daemonset: 'DaemonSet',
  replicaset: 'ReplicaSet', pod: 'Pod', service: 'Service', ingress: 'Ingress',
  configmap: 'ConfigMap', secret: 'Secret', pvc: 'PVC',
  serviceaccount: 'ServiceAccount', namespace: 'Namespace',
  internet: 'Internet', zone: 'Network Zone',
}

export default {
  name: 'WorkloadGraph',

  props: {
    workloadData: { type: Object, default: () => ({}) },
    focusNodeId: { type: String, default: null },
    fullscreen: { type: Boolean, default: false },
  },

  emits: ['node-selected', 'related-nodes'],

  data() {
    return {
      cy: null,
      layoutName: 'fcose',
      selected: null,
      selectedEdges: [],
      namespaceCounts: {},
      isEmpty: false,
      layoutRunning: false,
      resizeObserver: null,
      themeObserver: null,
      flowAnimFrame: null,
      flowOffset: 0,
    }
  },

  computed: {
    selectedTypeLabel() {
      return TYPE_LABELS[this.selected?.nodeType] || this.selected?.nodeType || ''
    },
    selectedBadgeClass() {
      const type = this.selected?.nodeType
      const map = {
        deployment: 'bg-blue-100 text-blue-700',
        statefulset: 'bg-violet-100 text-violet-700',
        daemonset: 'bg-indigo-100 text-indigo-700',
        replicaset: 'bg-blue-50 text-blue-600',
        pod: 'bg-green-100 text-green-700',
        service: 'bg-amber-100 text-amber-700',
        ingress: 'bg-orange-100 text-orange-700',
        configmap: 'bg-cyan-100 text-cyan-700',
        secret: 'bg-red-100 text-red-700',
        pvc: 'bg-purple-100 text-purple-700',
        serviceaccount: 'bg-teal-100 text-teal-700',
        internet: 'bg-blue-100 text-blue-800',
        zone: 'bg-blue-50 text-blue-700',
        namespace: 'bg-gray-100 text-gray-700',
      }
      return map[type] || 'bg-gray-100 text-gray-700'
    },
  },

  watch: {
    workloadData: {
      handler() { this.rebuild() },
      deep: true,
    },
    focusNodeId(id) {
      if (id) this.focusOnNode(id)
      else this.clearSelection()
    },
  },

  mounted() {
    this.initCytoscape()
    this.rebuild()

    this.resizeObserver = new ResizeObserver(() => {
      if (this.cy) this.cy.resize()
    })
    this.resizeObserver.observe(this.$refs.cyContainer)

    this.themeObserver = new MutationObserver(() => this.applyStyles())
    this.themeObserver.observe(document.documentElement, {
      attributes: true, attributeFilter: ['data-theme'],
    })
  },

  beforeUnmount() {
    this.stopFlowAnimation()
    if (this.cy) this.cy.destroy()
    if (this.resizeObserver) this.resizeObserver.disconnect()
    if (this.themeObserver) this.themeObserver.disconnect()
  },

  methods: {
    initCytoscape() {
      this.cy = cytoscape({
        container: this.$refs.cyContainer,
        elements: [],
        style: this.buildStylesheet(),
        layout: { name: 'preset' },
        minZoom: 0.1,
        maxZoom: 3,
        wheelSensitivity: 0.3,
        textureOnViewport: true,
        hideEdgesOnViewport: true,
        hideLabelsOnViewport: true,
        pixelRatio: 1,
      })

      this.cy.on('tap', 'node', (evt) => this.selectNode(evt.target))
      this.cy.on('tap', (evt) => {
        if (evt.target === this.cy) this.clearSelection()
      })

      // Track grab position so we can skip the expensive overlap resolution
      // when the user just clicks without actually dragging.
      let grabPos = null
      this.cy.on('grab', 'node', (evt) => {
        const p = evt.target.position()
        grabPos = { x: p.x, y: p.y }
      })

      // On drag end, cascade-push all overlapping nodes.
      // Uses instant shift() in a multi-pass loop so pushed nodes push their
      // neighbors too, then resolveCompoundOverlaps cleans up any remaining issues.
      this.cy.on('free', 'node', (evt) => {
        const node = evt.target
        // Skip if node wasn't actually moved (just clicked)
        if (grabPos) {
          const p = node.position()
          if (Math.abs(p.x - grabPos.x) < 1 && Math.abs(p.y - grabPos.y) < 1) {
            grabPos = null
            return
          }
        }
        grabPos = null
        const margin = 35

        this.cy.batch(() => {
          if (!node.isParent()) {
            // Leaf dragged: push it out of foreign outermost compounds first
            const ancestorIds = new Set()
            let anc = node.parent()
            while (anc && anc.length > 0) { ancestorIds.add(anc.id()); anc = anc.parent() }

            this.cy.nodes(':parent').forEach(compound => {
              if (ancestorIds.has(compound.id())) return
              const ct = compound.data('nodeType')
              if (ct === 'namespace' || ct === 'zone') return
              const cp = compound.parent()
              if (cp.length) {
                const cpt = cp.data('nodeType')
                if (cpt !== 'namespace' && cpt !== 'zone') return
              }

              const lBB = node.boundingBox({ includeLabels: true })
              const cBB = compound.boundingBox({ includeLabels: true })
              if (lBB.x2 < cBB.x1 || lBB.x1 > cBB.x2 || lBB.y2 < cBB.y1 || lBB.y1 > cBB.y2) return

              const pos = node.position()
              const cx = (cBB.x1 + cBB.x2) / 2
              const cy = (cBB.y1 + cBB.y2) / 2
              const dx = pos.x - cx
              const dy = pos.y - cy
              const hw = (cBB.x2 - cBB.x1) / 2 + margin
              const hh = (cBB.y2 - cBB.y1) / 2 + margin
              if (Math.abs(dx) / hw > Math.abs(dy) / hh) {
                node.position({ x: cx + Math.sign(dx || 1) * hw, y: pos.y })
              } else {
                node.position({ x: pos.x, y: cy + Math.sign(dy || 1) * hh })
              }
            })
          }

          // Multi-pass: push all overlapping non-namespace/zone nodes apart.
          // Each pass may displace nodes into new overlaps, so iterate.
          // Skip if too many nodes — O(n^2) would lock the browser.
          const skipTypes = new Set(['namespace', 'zone'])
          const allNodes = this.cy.nodes(':visible').filter(n => !skipTypes.has(n.data('nodeType')))

          if (allNodes.length > 80) return // too many nodes for pairwise check

          for (let pass = 0; pass < 12; pass++) {
            let moved = false
            for (let i = 0; i < allNodes.length; i++) {
              for (let j = i + 1; j < allNodes.length; j++) {
                const a = allNodes[i]
                const b = allNodes[j]

                // Skip if one is an ancestor/descendant of the other
                if (a.isParent() && b.ancestors().includes(a)) continue
                if (b.isParent() && a.ancestors().includes(b)) continue
                if (a.parent().id() !== b.parent().id() && !a.isParent() && !b.isParent()) {
                  // Different parents and both leaves — skip (handled by sibling pass)
                  continue
                }

                const aBB = a.boundingBox({ includeLabels: true })
                const bBB = b.boundingBox({ includeLabels: true })
                const overlapX = Math.min(aBB.x2 + margin, bBB.x2 + margin) - Math.max(aBB.x1 - margin, bBB.x1 - margin)
                const overlapY = Math.min(aBB.y2 + margin, bBB.y2 + margin) - Math.max(aBB.y1 - margin, bBB.y1 - margin)
                if (overlapX <= 0 || overlapY <= 0) continue

                moved = true
                if (overlapX < overlapY) {
                  const shift = overlapX / 2 + 1
                  const dir = (aBB.x1 + aBB.x2) <= (bBB.x1 + bBB.x2) ? -1 : 1
                  a.shift({ x: dir * shift, y: 0 })
                  b.shift({ x: -dir * shift, y: 0 })
                } else {
                  const shift = overlapY / 2 + 1
                  const dir = (aBB.y1 + aBB.y2) <= (bBB.y1 + bBB.y2) ? -1 : 1
                  a.shift({ x: 0, y: dir * shift })
                  b.shift({ x: 0, y: -dir * shift })
                }
              }
            }
            if (!moved) break
          }
        })

        // Run full overlap resolution for any edge cases
        this.resolveCompoundOverlaps(false)
      })
    },

    buildStylesheet() {
      const colors = this.getThemeColors()
      const styles = [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'font-size': '9px',
            'font-family': 'system-ui, sans-serif',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-wrap': 'wrap',
            'text-max-width': '200px',
            'text-margin-y': 4,
            'width': 35,
            'height': 35,
            'border-width': 2,
            'text-background-color': colors.canvasBg,
            'text-background-opacity': 1,
            'text-background-padding': '3px',
            'text-background-shape': 'roundrectangle',
            'z-compound-depth': 'top',
            'z-index': 10,
          },
        },
        {
          selector: 'node[nodeType="namespace"]',
          style: {
            'shape': 'round-rectangle',
            'background-color': colors.namespaceBg,
            'background-opacity': 0.15,
            'border-color': colors.namespaceBorder,
            'border-width': 1,
            'border-style': 'dashed',
            'font-size': '13px',
            'font-weight': 'bold',
            'text-valign': 'top',
            'text-halign': 'center',
            'text-margin-y': -8,
            'color': colors.namespaceText,
            'text-outline-width': 0,
            'padding': '60px',
          },
        },
        // Zone compound nodes (e.g., "External") — blue-tinted background
        {
          selector: 'node[nodeType="zone"]',
          style: {
            'shape': 'round-rectangle',
            'background-color': '#dbeafe',
            'background-opacity': 0.2,
            'border-color': '#93c5fd',
            'border-width': 2,
            'border-style': 'solid',
            'font-size': '13px',
            'font-weight': 'bold',
            'text-valign': 'top',
            'text-halign': 'center',
            'text-margin-y': -8,
            'color': '#1e40af',
            'text-outline-width': 0,
            'padding': '30px',
          },
        },
        // Internet node — large dark blue circle
        {
          selector: 'node[nodeType="internet"]',
          style: {
            'shape': 'ellipse',
            'background-color': '#1e40af',
            'border-color': '#1e3a8a',
            'border-width': 3,
            'color': '#1e40af',
            'width': 50,
            'height': 50,
            'font-size': '11px',
            'font-weight': 'bold',
          },
        },
      ]

      // Compound styles for controllers (Deployment, StatefulSet, DaemonSet)
      // These are parent nodes containing RS/Pods, so they need container styling.
      const compoundTypes = {
        deployment:  { bg: '#3b82f6', border: '#2563eb', text: '#2563eb' },
        statefulset: { bg: '#8b5cf6', border: '#7c3aed', text: '#7c3aed' },
        daemonset:   { bg: '#6366f1', border: '#4f46e5', text: '#4f46e5' },
        replicaset:  { bg: '#60a5fa', border: '#3b82f6', text: '#2563eb' },
      }
      for (const [type, c] of Object.entries(compoundTypes)) {
        styles.push({
          selector: `node[nodeType="${type}"]`,
          style: {
            'shape': 'round-rectangle',
            'background-color': c.bg,
            'background-opacity': 0.1,
            'border-color': c.border,
            'border-width': 2,
            'border-style': 'solid',
            'font-size': '11px',
            'font-weight': 'bold',
            'text-valign': 'top',
            'text-halign': 'center',
            'text-margin-y': -6,
            'text-wrap': 'wrap',
            'text-max-width': '200px',
            'color': c.text,
            'text-outline-width': 0,
            'padding': '40px',
          },
        })
      }

      // Per-type styles (leaf nodes only — excludes compound controller types)
      const compoundSet = new Set(Object.keys(compoundTypes))
      for (const [type, color] of Object.entries(NODE_COLORS)) {
        if (type === 'namespace' || compoundSet.has(type)) continue
        const size = NODE_SIZES[type] || 35
        styles.push({
          selector: `node[nodeType="${type}"]`,
          style: {
            'shape': NODE_SHAPES[type],
            'background-color': color.bg,
            'border-color': color.border,
            'color': color.border,
            'width': size,
            'height': size,
          },
        })
      }

      // Pod phase override colors
      for (const [phase, phaseColor] of Object.entries(POD_PHASE_COLORS)) {
        styles.push({
          selector: `node[nodeType="pod"][phase="${phase}"]`,
          style: {
            'background-color': phaseColor.bg,
            'border-color': phaseColor.border,
            'color': phaseColor.border,
          },
        })
      }

      // Base edge style (owns = default)
      // Base edge — solid, cheap to render. Use haystack for non-compound edges.
      styles.push({
        selector: 'edge',
        style: {
          'width': 1.5,
          'curve-style': 'straight',
          'target-arrow-shape': 'triangle',
          'target-arrow-color': EDGE_COLORS.owns,
          'line-color': EDGE_COLORS.owns,
          'arrow-scale': 0.7,
          'opacity': 0.6,
        },
      })
      // Edges connecting to compound nodes need bezier curves
      styles.push({
        selector: 'edge[edgeType="selects"], edge[edgeType="routes"], edge[edgeType="external"], edge[edgeType="mounts"]',
        style: { 'curve-style': 'bezier' },
      })

      // Animated flow edges — dashed lines with animated offset
      styles.push(
        {
          selector: 'edge[edgeType="selects"]',
          style: {
            'line-color': EDGE_COLORS.selects, 'target-arrow-color': EDGE_COLORS.selects,
            'line-style': 'dashed', 'line-dash-pattern': [8, 4],
            'width': 2, 'opacity': 0.85,
          },
        },
        {
          selector: 'edge[edgeType="routes"]',
          style: {
            'line-color': EDGE_COLORS.routes, 'target-arrow-color': EDGE_COLORS.routes,
            'line-style': 'dashed', 'line-dash-pattern': [8, 4],
            'width': 2, 'opacity': 0.85,
          },
        },
        {
          selector: 'edge[edgeType="external"]',
          style: {
            'line-color': EDGE_COLORS.external, 'target-arrow-color': EDGE_COLORS.external,
            'line-style': 'dashed', 'line-dash-pattern': [10, 5],
            'width': 3, 'opacity': 0.9,
          },
        },
        {
          selector: 'edge[edgeType="mounts"]',
          style: {
            'line-color': EDGE_COLORS.mounts, 'target-arrow-color': EDGE_COLORS.mounts,
            'target-arrow-shape': 'diamond',
            'line-style': 'dashed', 'line-dash-pattern': [6, 4],
            'width': 2, 'opacity': 0.85,
          },
        },
        {
          selector: 'edge[edgeType="usessa"]',
          style: {
            'line-color': EDGE_COLORS.usessa, 'target-arrow-color': EDGE_COLORS.usessa,
            'target-arrow-shape': 'diamond',
          },
        },
      )

      // Highlighted state
      styles.push(
        {
          selector: 'node.highlighted',
          style: {
            'border-width': 4, 'border-color': '#2563eb',
            'overlay-opacity': 0.08, 'overlay-color': '#2563eb',
          },
        },
        {
          selector: 'edge.highlighted',
          style: { 'width': 3, 'opacity': 1 },
        },
      )

      return styles
    },

    getThemeColors() {
      const s = getComputedStyle(document.documentElement)
      const get = (prop, fallback) => s.getPropertyValue(prop).trim() || fallback
      return {
        canvasBg: get('--th-bg-card-alt', '#f9fafb'),
        namespaceBg: get('--th-border', '#e5e7eb'),
        namespaceBorder: get('--th-text-muted', '#9ca3af'),
        namespaceText: get('--th-text-secondary', '#6b7280'),
        edgeLabel: get('--th-text-muted', '#9ca3af'),
      }
    },

    applyStyles() {
      if (!this.cy) return
      this.cy.style(this.buildStylesheet())
    },

    rebuild() {
      if (!this.cy) return
      const { nodes, edges } = buildWorkloadElements(this.workloadData)

      this.cy.elements().remove()
      if (nodes.length === 0) {
        this.isEmpty = true
        return
      }
      this.isEmpty = false
      this.cy.add([...nodes, ...edges])
      this.clearSelection()
      this.runLayout()
    },

    runLayout() {
      if (!this.cy || this.cy.nodes().length === 0) return

      this.layoutRunning = true

      const layoutConfigs = {
        dagre: {
          name: 'dagre', rankDir: 'LR', nodeSep: 130, rankSep: 160, edgeSep: 60,
          animate: true, animationDuration: 300, fit: true, padding: 50,
          avoidOverlap: true,
        },
        fcose: {
          name: 'fcose', quality: 'default', animate: true, animationDuration: 300,
          fit: true, padding: 50, nodeSeparation: 400, idealEdgeLength: 300,
          nodeRepulsion: (node) => {
            const t = node.data('nodeType')
            if (t === 'namespace' || t === 'zone') return 500000
            if (node.isParent()) return 200000
            return 100000
          },
          edgeElasticity: 0.3, gravity: 0.06,
          gravityRange: 8, nestingFactor: 0.02, numIter: 2500,
          tile: true, tilingPaddingVertical: 100, tilingPaddingHorizontal: 100,
          avoidOverlap: true,
        },
        cose: {
          name: 'cose', animate: true, animationDuration: 300, fit: true, padding: 50,
          nodeRepulsion: (node) => {
            const t = node.data('nodeType')
            if (t === 'namespace' || t === 'zone') return 500000
            if (node.isParent()) return 200000
            return 100000
          },
          idealEdgeLength: (edge) => edge.source().isParent() || edge.target().isParent() ? 400 : 250,
          edgeElasticity: 100, gravity: 0.06, nestingFactor: 8,
          avoidOverlap: true, nodeOverlap: 60,
        },
        concentric: {
          name: 'concentric', animate: true, animationDuration: 300, fit: true, padding: 50,
          minNodeSpacing: 100, concentric: (node) => node.connectedEdges().length, levelWidth: () => 2,
          avoidOverlap: true,
        },
        breadthfirst: {
          name: 'breadthfirst', directed: true, animate: true, animationDuration: 300,
          fit: true, padding: 50, spacingFactor: 1.8,
          avoidOverlap: true,
        },
        circle: {
          name: 'circle', animate: true, animationDuration: 300, fit: true, padding: 50, spacingFactor: 1.8,
          avoidOverlap: true,
        },
      }

      const opts = layoutConfigs[this.layoutName] || layoutConfigs.fcose
      const done = () => {
        this.resolveCompoundOverlaps()
        this.layoutRunning = false
        this.startFlowAnimation()
      }
      opts.stop = done

      // Pin the Internet node at center so namespaces arrange around it
      const inetNode = this.cy.getElementById('internet')
      if (inetNode && inetNode.length > 0) {
        const w = this.cy.width()
        const h = this.cy.height()
        const cx = w / 2
        const cy = h / 2

        if (opts.name === 'fcose') {
          opts.fixedNodeConstraint = [{ nodeId: 'internet', position: { x: cx, y: cy } }]
        } else if (opts.name === 'cose') {
          // cose doesn't support constraints — pre-position and lock
          inetNode.position({ x: cx, y: cy })
          inetNode.lock()
          opts.stop = () => { inetNode.unlock(); done() }
        } else if (opts.name === 'dagre') {
          inetNode.position({ x: 0, y: cy })
          inetNode.lock()
          opts.stop = () => { inetNode.unlock(); done() }
        }
      }

      // Double rAF ensures the browser paints the loading overlay before layout blocks the thread
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (this.cy) this.cy.layout(opts).run()
        })
      })
    },

    startFlowAnimation() {
      this.stopFlowAnimation()
      if (!this.cy) return
      const animatedEdges = this.cy.edges('[edgeType="external"], [edgeType="routes"], [edgeType="selects"], [edgeType="mounts"]')
      if (animatedEdges.length === 0) return

      let lastTime = 0
      const tick = (time) => {
        if (time - lastTime < 66) { // ~15fps
          this.flowAnimFrame = requestAnimationFrame(tick)
          return
        }
        lastTime = time
        this.flowOffset = (this.flowOffset + 1) % 24
        this.cy.batch(() => {
          animatedEdges.forEach(edge => {
            edge.style('line-dash-offset', -this.flowOffset)
          })
        })
        this.flowAnimFrame = requestAnimationFrame(tick)
      }
      this.flowAnimFrame = requestAnimationFrame(tick)
    },

    stopFlowAnimation() {
      if (this.flowAnimFrame) {
        cancelAnimationFrame(this.flowAnimFrame)
        this.flowAnimFrame = null
      }
    },

    // Post-layout pass: push apart overlapping compound nodes.
    // Batched to minimize re-renders. Max 15 passes.
    resolveCompoundOverlaps(fitAfter = true) {
      if (!this.cy) return
      const margin = 45
      const compounds = this.cy.nodes(':parent').filter(n => {
        const t = n.data('nodeType')
        return t !== 'namespace' && t !== 'zone'
      })
      if (compounds.length < 2) return

      // Pre-compute parent IDs to avoid repeated DOM queries
      const parentIdMap = new Map()
      compounds.forEach(c => {
        const p = c.parent()
        parentIdMap.set(c.id(), p.length ? p.id() : null)
      })

      this.cy.batch(() => {
        for (let pass = 0; pass < 15; pass++) {
          let moved = false
          for (let i = 0; i < compounds.length; i++) {
            for (let j = i + 1; j < compounds.length; j++) {
              const a = compounds[i]
              const b = compounds[j]
              if (parentIdMap.get(a.id()) !== parentIdMap.get(b.id())) continue

              const aBB = a.boundingBox({ includeLabels: true })
              const bBB = b.boundingBox({ includeLabels: true })
              const overlapX = Math.min(aBB.x2 + margin, bBB.x2 + margin) - Math.max(aBB.x1 - margin, bBB.x1 - margin)
              const overlapY = Math.min(aBB.y2 + margin, bBB.y2 + margin) - Math.max(aBB.y1 - margin, bBB.y1 - margin)
              if (overlapX <= 0 || overlapY <= 0) continue

              moved = true
              const aCx = (aBB.x1 + aBB.x2) / 2
              const bCx = (bBB.x1 + bBB.x2) / 2
              const aCy = (aBB.y1 + aBB.y2) / 2
              const bCy = (bBB.y1 + bBB.y2) / 2

              if (overlapX < overlapY) {
                const shift = overlapX / 2 + 1
                const dir = aCx <= bCx ? -1 : 1
                a.shift({ x: dir * shift, y: 0 })
                b.shift({ x: -dir * shift, y: 0 })
              } else {
                const shift = overlapY / 2 + 1
                const dir = aCy <= bCy ? -1 : 1
                a.shift({ x: 0, y: dir * shift })
                b.shift({ x: 0, y: -dir * shift })
              }
            }
          }
          if (!moved) break
        }
      })

      // Push leaf nodes out of foreign compounds — only for visible, non-child leaves.
      // Only check against outermost compounds (parent is namespace/zone/root),
      // NOT nested compounds like RS inside Deploy. Otherwise a leaf gets pushed
      // to the inner compound edge instead of the outer one.
      const nestedTypes = new Set(['deployment', 'statefulset', 'daemonset', 'replicaset'])
      const outermostCompounds = this.cy.nodes(':parent').filter(n => {
        const t = n.data('nodeType')
        if (t === 'namespace' || t === 'zone') return false // skip namespaces/zones themselves
        const p = n.parent()
        if (!p.length) return true // root-level compound
        const pt = p.data('nodeType')
        return pt === 'namespace' || pt === 'zone' // parent is namespace/zone = outermost
      })
      const leaves = this.cy.nodes(':childless:visible')
      if (leaves.length * outermostCompounds.length > 50000) {
        // Skip for very large graphs to prevent freeze
        this.cy.fit(undefined, 30)
        return
      }

      this.cy.batch(() => {
        leaves.forEach(leaf => {
          const ancestorIds = new Set()
          let anc = leaf.parent()
          while (anc && anc.length > 0) {
            ancestorIds.add(anc.id())
            anc = anc.parent()
          }

          outermostCompounds.forEach(compound => {
            if (ancestorIds.has(compound.id())) return
            const lBB = leaf.boundingBox({ includeLabels: true })
            const cBB = compound.boundingBox({ includeLabels: true })
            if (lBB.x2 < cBB.x1 - margin || lBB.x1 > cBB.x2 + margin ||
                lBB.y2 < cBB.y1 - margin || lBB.y1 > cBB.y2 + margin) return

            const pos = leaf.position()
            const cx = (cBB.x1 + cBB.x2) / 2
            const cy = (cBB.y1 + cBB.y2) / 2
            const dx = pos.x - cx
            const dy = pos.y - cy
            const hw = (cBB.x2 - cBB.x1) / 2 + margin
            const hh = (cBB.y2 - cBB.y1) / 2 + margin
            if (Math.abs(dx) / hw > Math.abs(dy) / hh) {
              leaf.position({ x: cx + Math.sign(dx || 1) * hw, y: pos.y })
            } else {
              leaf.position({ x: pos.x, y: cy + Math.sign(dy || 1) * hh })
            }
          })
        })
      })

      // Push apart overlapping sibling leaf nodes (same parent).
      // Only for leaves inside namespaces or at root — NOT inside controller/RS
      // compounds, since pushing children apart would expand the compound box.
      const compoundNodeTypes = new Set(['deployment', 'statefulset', 'daemonset', 'replicaset'])
      const leafMargin = 35
      const siblingGroups = new Map()
      leaves.forEach(leaf => {
        const p = leaf.parent()
        const pid = p.length ? p.id() : '__root__'
        // Skip leaves inside controller/RS compounds
        if (p.length && compoundNodeTypes.has(p.data('nodeType'))) return
        if (!siblingGroups.has(pid)) siblingGroups.set(pid, [])
        siblingGroups.get(pid).push(leaf)
      })

      this.cy.batch(() => {
        for (const [, siblings] of siblingGroups) {
          if (siblings.length < 2) continue
          for (let pass = 0; pass < 10; pass++) {
            let moved = false
            for (let i = 0; i < siblings.length; i++) {
              for (let j = i + 1; j < siblings.length; j++) {
                const a = siblings[i]
                const b = siblings[j]
                const aBB = a.boundingBox({ includeLabels: true })
                const bBB = b.boundingBox({ includeLabels: true })
                const overlapX = Math.min(aBB.x2 + leafMargin, bBB.x2 + leafMargin) - Math.max(aBB.x1 - leafMargin, bBB.x1 - leafMargin)
                const overlapY = Math.min(aBB.y2 + leafMargin, bBB.y2 + leafMargin) - Math.max(aBB.y1 - leafMargin, bBB.y1 - leafMargin)
                if (overlapX <= 0 || overlapY <= 0) continue

                moved = true
                const aCx = (aBB.x1 + aBB.x2) / 2
                const bCx = (bBB.x1 + bBB.x2) / 2
                const aCy = (aBB.y1 + aBB.y2) / 2
                const bCy = (bBB.y1 + bBB.y2) / 2

                if (overlapX < overlapY) {
                  const shift = overlapX / 2 + 1
                  const dir = aCx <= bCx ? -1 : 1
                  a.shift({ x: dir * shift, y: 0 })
                  b.shift({ x: -dir * shift, y: 0 })
                } else {
                  const shift = overlapY / 2 + 1
                  const dir = aCy <= bCy ? -1 : 1
                  a.shift({ x: 0, y: dir * shift })
                  b.shift({ x: 0, y: -dir * shift })
                }
              }
            }
            if (!moved) break
          }
        }
      })

      if (fitAfter) this.cy.fit(undefined, 30)
    },

    runSubLayout(elements) {
      const subConfigs = {
        dagre: {
          name: 'dagre', rankDir: 'LR', nodeSep: 80, rankSep: 110,
          animate: true, animationDuration: 300, fit: true, padding: 50,
          avoidOverlap: true,
        },
        fcose: {
          name: 'fcose', quality: 'default', animate: true, animationDuration: 300,
          fit: true, padding: 50, nodeSeparation: 200, idealEdgeLength: 180,
          nodeRepulsion: 30000, edgeElasticity: 0.35, gravity: 0.1,
          numIter: 500, tile: true,
          avoidOverlap: true,
        },
        cose: {
          name: 'cose', animate: true, animationDuration: 300, fit: true, padding: 50,
          nodeRepulsion: 30000, idealEdgeLength: 180, edgeElasticity: 100, gravity: 0.1,
          avoidOverlap: true, nodeOverlap: 40,
        },
        concentric: {
          name: 'concentric', animate: true, animationDuration: 300, fit: true, padding: 50,
          minNodeSpacing: 70, concentric: (node) => node.connectedEdges().length, levelWidth: () => 2,
          avoidOverlap: true,
        },
        breadthfirst: {
          name: 'breadthfirst', directed: true, animate: true, animationDuration: 300,
          fit: true, padding: 50, spacingFactor: 1.3,
          avoidOverlap: true,
        },
        circle: {
          name: 'circle', animate: true, animationDuration: 300, fit: true, padding: 50, spacingFactor: 1.4,
          avoidOverlap: true,
        },
      }
      const opts = subConfigs[this.layoutName] || subConfigs.fcose
      elements.layout(opts).run()
    },

    fitGraph() {
      if (this.cy) this.cy.fit(undefined, 30)
    },

    focusOnNode(nodeId) {
      if (!this.cy) return
      const node = this.cy.getElementById(nodeId)
      if (!node || node.length === 0) return
      this.selectNode(node)
    },

    selectNode(node) {
      this.cy.elements().removeClass('highlighted')

      const data = node.data()
      this.selected = data
      this.$emit('node-selected', node.id())

      // Namespace/zone nodes: just highlight, don't drill down (too many children)
      const nt = data.nodeType
      if (nt === 'namespace' || nt === 'zone') {
        node.addClass('highlighted')
        return
      }

      // Collect all relevant node IDs first (cheap Set operations),
      // then build the Cytoscape collection once at the end.
      const visited = new Set()
      const nodeList = []

      const enqueue = (n) => {
        const nid = n.id()
        if (visited.has(nid)) return
        visited.add(nid)
        nodeList.push(n)
      }

      // Seed: the clicked node + all its descendants
      const addDescendants = (n) => {
        enqueue(n)
        if (n.isParent()) {
          n.children().forEach(child => addDescendants(child))
        }
      }
      addDescendants(node)

      // Walk up to ancestors (controller → namespace)
      let parent = node.parent()
      while (parent && parent.length > 0) {
        enqueue(parent)
        parent = parent.parent()
      }

      // Expand: for every leaf node so far, follow edges to connected resources
      const frontierEnd = nodeList.length
      for (let i = 0; i < frontierEnd; i++) {
        const n = nodeList[i]
        if (n.isParent()) continue
        n.connectedEdges().forEach(edge => {
          const other = edge.source().id() === n.id() ? edge.target() : edge.source()
          enqueue(other)
          let p = other.parent()
          while (p && p.length > 0) {
            enqueue(p)
            p = p.parent()
          }
        })
      }

      // Build collection: all visited nodes + edges where both endpoints are visited
      // Use union() once instead of repeated merge() calls (O(n) vs O(n^2))
      let visible = this.cy.collection().union(this.cy.nodes().filter(n => visited.has(n.id())))
      const visibleEdges = this.cy.edges().filter(edge =>
        visited.has(edge.source().id()) && visited.has(edge.target().id())
      )
      visible = visible.union(visibleEdges)

      // Isolate: hide everything, show only collected elements
      this.cy.batch(() => {
        this.cy.elements().hide()
        visible.show()
        node.addClass('highlighted')
        const connected = node.connectedEdges().filter(e => visited.has(e.source().id()) && visited.has(e.target().id()))
        connected.connectedNodes().addClass('highlighted')
        connected.addClass('highlighted')
      })

      // Re-layout visible subgraph using currently selected layout
      this.runSubLayout(visible)

      // Emit related node IDs
      const relatedIds = new Set(visited)
      this.$emit('related-nodes', relatedIds)

      // Build edge metadata for detail panel
      this.buildEdgeDetails(node)

      // Build namespace counts if namespace node
      if (data.nodeType === 'namespace') {
        this.buildNamespaceCounts(node)
      }
    },

    buildEdgeDetails(node) {
      const edges = []
      node.connectedEdges().forEach(edge => {
        const sourceId = edge.source().id()
        const targetId = edge.target().id()
        const isOutgoing = sourceId === node.id()
        const otherNode = isOutgoing ? edge.target() : edge.source()
        edges.push({
          id: edge.id(),
          edgeType: edge.data('edgeType') || 'unknown',
          label: edge.data('label') || '',
          targetLabel: otherNode.data('label') || otherNode.id(),
          targetType: otherNode.data('nodeType'),
          direction: isOutgoing ? 'out' : 'in',
        })
      })
      this.selectedEdges = edges
    },

    buildNamespaceCounts(nsNode) {
      const counts = {}
      nsNode.children().forEach(child => {
        const type = child.data('nodeType')
        const label = TYPE_LABELS[type] || type
        counts[label] = (counts[label] || 0) + 1
      })
      this.namespaceCounts = counts
    },

    clearSelection() {
      this.selected = null
      this.selectedEdges = []
      this.namespaceCounts = {}
      this.$emit('node-selected', null)
      this.$emit('related-nodes', new Set())
      if (this.cy) {
        this.cy.elements().show()
        this.cy.elements().removeClass('highlighted')
        this.runLayout()
      }
    },

    podPhaseClass(phase) {
      const map = {
        Running: 'bg-green-100 text-green-700',
        Pending: 'bg-yellow-100 text-yellow-700',
        Succeeded: 'bg-blue-100 text-blue-700',
        Failed: 'bg-red-100 text-red-700',
      }
      return map[phase] || 'bg-gray-100 text-gray-700'
    },
  },
}
</script>
