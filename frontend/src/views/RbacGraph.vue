<template>
  <div class="relative" ref="wrapper">
    <!-- Toolbar -->
    <div class="absolute top-3 right-3 z-10 flex gap-1.5">
      <button @click="fitGraph" title="Fit to view"
        class="w-8 h-8 flex items-center justify-center rounded bg-white/90 border border-gray-200 text-gray-600 hover:bg-gray-100 cursor-pointer text-sm shadow-sm"
        style="background-color: var(--th-bg-card, #fff); border-color: var(--th-border, #e5e7eb); color: var(--th-text-secondary, #6b7280);">
        <font-awesome-icon :icon="['fas', 'arrows-rotate']" />
      </button>
      <button @click="toggleLayout" :title="`Layout: ${layoutName}`"
        class="w-8 h-8 flex items-center justify-center rounded bg-white/90 border border-gray-200 text-gray-600 hover:bg-gray-100 cursor-pointer text-sm shadow-sm"
        style="background-color: var(--th-bg-card, #fff); border-color: var(--th-border, #e5e7eb); color: var(--th-text-secondary, #6b7280);">
        <font-awesome-icon :icon="['fas', 'layer-group']" />
      </button>
    </div>

    <!-- Legend -->
    <div class="absolute bottom-3 left-3 z-10 rounded-lg p-3 shadow-sm border text-xs space-y-1.5"
      style="background-color: var(--th-bg-card, #fff); border-color: var(--th-border, #e5e7eb); color: var(--th-text, #374151);">
      <div class="font-medium mb-1" style="color: var(--th-text-heading, #2c3e50);">Legend</div>
      <div class="flex items-center gap-2">
        <span class="w-3 h-3 rounded-sm bg-blue-500 inline-block"></span> ServiceAccount
      </div>
      <div class="flex items-center gap-2">
        <span class="w-3 h-3 rounded-sm bg-purple-500 inline-block"></span> Role
      </div>
      <div class="flex items-center gap-2">
        <span class="w-3 h-3 rounded-sm bg-amber-500 inline-block"></span> ClusterRole
      </div>
      <div class="flex items-center gap-2">
        <span class="w-3 h-3 rounded-sm bg-gray-400 inline-block border border-gray-300"></span> Namespace
      </div>
      <hr class="border-gray-200 my-1" style="border-color: var(--th-border-light, #f3f4f6);">
      <div class="flex items-center gap-2">
        <span class="w-4 border-t-2 border-green-500 inline-block"></span> RoleBinding
      </div>
      <div class="flex items-center gap-2">
        <span class="w-4 border-t-2 border-dashed border-teal-500 inline-block"></span> ClusterRoleBinding
      </div>
    </div>

    <!-- Cytoscape container -->
    <div ref="cyContainer" class="w-full rounded-lg border"
      style="height: calc(100vh - 220px); background-color: var(--th-bg-card-alt, #f9fafb); border-color: var(--th-border, #e5e7eb);"></div>

    <!-- Empty state -->
    <div v-if="isEmpty" class="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div class="text-center">
        <p class="text-gray-400 text-sm">No RBAC relationships to display.</p>
        <p class="text-gray-300 text-xs mt-1">Create users with bindings to see the graph.</p>
      </div>
    </div>

    <!-- Detail panel -->
    <div v-if="selected" class="absolute top-0 right-0 w-64 h-full rounded-r-lg border-l overflow-y-auto shadow-lg"
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

        <!-- SA details: show bound roles -->
        <div v-if="selected.nodeType === 'serviceaccount'">
          <h5 class="text-sm font-medium mb-2" style="color: var(--th-text, #374151);">Bound Roles</h5>
          <div v-if="selectedEdges.length === 0" class="text-xs italic" style="color: var(--th-text-muted, #9ca3af);">No bindings found</div>
          <div v-for="edge in selectedEdges" :key="edge.id" class="text-sm py-1.5 border-b"
            style="border-color: var(--th-border-light, #f3f4f6); color: var(--th-text, #374151);">
            <div class="font-medium">{{ edge.targetLabel }}</div>
            <div class="text-xs" style="color: var(--th-text-muted, #9ca3af);">via {{ edge.label }} ({{ edge.edgeType === 'rolebinding' ? 'RoleBinding' : 'ClusterRoleBinding' }})</div>
          </div>
        </div>

        <!-- Role / ClusterRole details: show rules + bound SAs -->
        <div v-if="selected.nodeType === 'role' || selected.nodeType === 'clusterrole'">
          <h5 class="text-sm font-medium mb-2" style="color: var(--th-text, #374151);">Rules</h5>
          <div v-if="!selected.raw || !selected.raw.rules || selected.raw.rules.length === 0"
            class="text-xs italic" style="color: var(--th-text-muted, #9ca3af);">No rules defined</div>
          <div v-else>
            <div v-for="(rule, idx) in selected.raw.rules" :key="idx" class="text-sm py-1.5 border-b"
              style="border-color: var(--th-border-light, #f3f4f6); color: var(--th-text, #374151);">
              {{ describeRule(rule) }}
            </div>
          </div>

          <h5 class="text-sm font-medium mt-4 mb-2" style="color: var(--th-text, #374151);">Bound ServiceAccounts</h5>
          <div v-if="selectedEdges.length === 0" class="text-xs italic" style="color: var(--th-text-muted, #9ca3af);">No bindings found</div>
          <div v-for="edge in selectedEdges" :key="edge.id" class="text-sm py-1.5 border-b"
            style="border-color: var(--th-border-light, #f3f4f6); color: var(--th-text, #374151);">
            <div class="font-medium">{{ edge.sourceLabel }}</div>
            <div class="text-xs" style="color: var(--th-text-muted, #9ca3af);">via {{ edge.label }}</div>
          </div>
        </div>

        <!-- Namespace details -->
        <div v-if="selected.nodeType === 'namespace'">
          <h5 class="text-sm font-medium mb-2" style="color: var(--th-text, #374151);">Contents</h5>
          <div class="text-sm space-y-1" style="color: var(--th-text, #374151);">
            <div>{{ selectedChildren.serviceaccounts }} ServiceAccount{{ selectedChildren.serviceaccounts !== 1 ? 's' : '' }}</div>
            <div>{{ selectedChildren.roles }} Role{{ selectedChildren.roles !== 1 ? 's' : '' }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import { buildElements } from '../services/rbacGraphBuilder'

cytoscape.use(dagre)

const NODE_COLORS = {
  serviceaccount: { bg: '#3b82f6', border: '#2563eb', text: '#ffffff' },
  role:           { bg: '#8b5cf6', border: '#7c3aed', text: '#ffffff' },
  clusterrole:    { bg: '#f59e0b', border: '#d97706', text: '#ffffff' },
  namespace:      { bg: '#e5e7eb', border: '#9ca3af', text: '#374151' },
}

const NODE_SHAPES = {
  serviceaccount: 'round-rectangle',
  role:           'rectangle',
  clusterrole:    'diamond',
  namespace:      'ellipse',
}

export default {
  name: 'RbacGraph',
  props: {
    serviceAccounts: { type: Array, default: () => [] },
    roles: { type: Array, default: () => [] },
    clusterRoles: { type: Array, default: () => [] },
    roleBindings: { type: Array, default: () => [] },
    clusterRoleBindings: { type: Array, default: () => [] },
    showSystem: { type: Boolean, default: false },
    focusNodeId: { type: String, default: null },
  },
  emits: ['node-selected', 'related-nodes'],
  data() {
    return {
      cy: null,
      layoutName: 'dagre',
      selected: null,
      selectedEdges: [],
      selectedChildren: { serviceaccounts: 0, roles: 0 },
      isEmpty: false,
      resizeObserver: null,
      themeObserver: null,
    }
  },
  computed: {
    selectedTypeLabel() {
      if (!this.selected) return ''
      return { serviceaccount: 'ServiceAccount', role: 'Role', clusterrole: 'ClusterRole', namespace: 'Namespace' }[this.selected.nodeType] || ''
    },
    selectedBadgeClass() {
      if (!this.selected) return ''
      return {
        serviceaccount: 'bg-blue-100 text-blue-700',
        role: 'bg-purple-100 text-purple-700',
        clusterrole: 'bg-amber-100 text-amber-700',
        namespace: 'bg-gray-100 text-gray-600',
      }[this.selected.nodeType] || 'bg-gray-100 text-gray-600'
    },
  },
  watch: {
    serviceAccounts() { this.rebuild() },
    roles() { this.rebuild() },
    clusterRoles() { this.rebuild() },
    roleBindings() { this.rebuild() },
    clusterRoleBindings() { this.rebuild() },
    showSystem() { this.rebuild() },
    focusNodeId(id) {
      if (!id) {
        this.clearSelection()
        return
      }
      this.focusOnNode(id)
    },
  },
  mounted() {
    this.initCytoscape()
    this.rebuild()

    // Resize handling
    this.resizeObserver = new ResizeObserver(() => {
      if (this.cy) {
        this.cy.resize()
        this.cy.fit(undefined, 30)
      }
    })
    this.resizeObserver.observe(this.$refs.cyContainer)

    // Theme change handling
    this.themeObserver = new MutationObserver(() => {
      this.applyStyles()
    })
    this.themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    })
  },
  beforeUnmount() {
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
        minZoom: 0.2,
        maxZoom: 3,
        wheelSensitivity: 0.3,
      })

      this.cy.on('tap', 'node', (evt) => {
        const node = evt.target
        this.selectNode(node)
      })

      this.cy.on('tap', (evt) => {
        if (evt.target === this.cy) {
          this.clearSelection()
        }
      })
    },

    buildStylesheet() {
      const colors = this.getThemeColors()
      const styles = [
        // Base node style
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'font-size': '11px',
            'font-family': 'system-ui, -apple-system, sans-serif',
            'text-valign': 'center',
            'text-halign': 'center',
            'text-wrap': 'ellipsis',
            'text-max-width': '100px',
            'width': 40,
            'height': 40,
            'border-width': 2,
            'text-outline-width': 2,
          },
        },
        // Compound (namespace) nodes
        {
          selector: 'node[nodeType="namespace"]',
          style: {
            'shape': 'round-rectangle',
            'background-color': colors.namespaceBg,
            'background-opacity': 0.15,
            'border-color': colors.namespaceBorder,
            'border-width': 1,
            'border-style': 'dashed',
            'label': 'data(label)',
            'font-size': '13px',
            'font-weight': 'bold',
            'text-valign': 'top',
            'text-halign': 'center',
            'text-margin-y': -8,
            'color': colors.namespaceText,
            'text-outline-width': 0,
            'padding': '20px',
          },
        },
      ]

      // Per-type node styles
      for (const [type, color] of Object.entries(NODE_COLORS)) {
        if (type === 'namespace') continue
        styles.push({
          selector: `node[nodeType="${type}"]`,
          style: {
            'shape': NODE_SHAPES[type],
            'background-color': color.bg,
            'border-color': color.border,
            'color': '#ffffff',
            'text-outline-color': color.bg,
          },
        })
      }

      // Edge styles
      styles.push(
        {
          selector: 'edge',
          style: {
            'width': 2,
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#22c55e',
            'line-color': '#22c55e',
            'arrow-scale': 0.8,
            'label': 'data(label)',
            'font-size': '9px',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
            'color': colors.edgeLabel,
            'text-outline-width': 2,
            'text-outline-color': colors.canvasBg,
            'opacity': 0.7,
          },
        },
        {
          selector: 'edge[edgeType="clusterrolebinding"]',
          style: {
            'line-style': 'dashed',
            'line-color': '#14b8a6',
            'target-arrow-color': '#14b8a6',
          },
        },
        // Highlighted state
        {
          selector: 'node:selected, node.highlighted',
          style: {
            'border-width': 4,
            'border-color': '#2563eb',
            'overlay-opacity': 0.08,
            'overlay-color': '#2563eb',
          },
        },
        {
          selector: 'edge.highlighted',
          style: {
            'width': 3,
            'opacity': 1,
          },
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

      const { nodes, edges } = buildElements(
        this.serviceAccounts, this.roles, this.clusterRoles,
        this.roleBindings, this.clusterRoleBindings,
      )

      this.isEmpty = nodes.length === 0 && edges.length === 0

      this.cy.elements().remove()
      this.cy.add([...nodes, ...edges])
      this.clearSelection()
      this.runLayout()
    },

    runLayout() {
      if (!this.cy || this.cy.nodes().length === 0) return

      const opts = this.layoutName === 'dagre'
        ? {
            name: 'dagre',
            rankDir: 'LR',
            nodeSep: 40,
            rankSep: 80,
            edgeSep: 20,
            animate: true,
            animationDuration: 300,
            fit: true,
            padding: 30,
          }
        : {
            name: 'cose',
            animate: true,
            animationDuration: 300,
            fit: true,
            padding: 30,
            nodeRepulsion: 8000,
            idealEdgeLength: 120,
            edgeElasticity: 100,
            gravity: 0.25,
          }

      this.cy.layout(opts).run()
    },

    fitGraph() {
      if (this.cy) this.cy.fit(undefined, 30)
    },

    toggleLayout() {
      this.layoutName = this.layoutName === 'dagre' ? 'cose' : 'dagre'
      this.runLayout()
    },

    focusOnNode(nodeId) {
      if (!this.cy) return
      const node = this.cy.getElementById(nodeId)
      if (!node || node.length === 0) return

      this.selectNode(node)
    },

    selectNode(node) {
      // Remove previous highlights
      this.cy.elements().removeClass('highlighted dimmed')

      const data = node.data()
      this.selected = data
      this.$emit('node-selected', node.id())

      // Traverse full connected component from the selected node
      const component = node.component()
      let visible = component

      // Also include parent namespace nodes for visible nodes
      visible.nodes().forEach(n => {
        const parent = n.parent()
        if (parent && parent.length > 0) {
          visible = visible.union(parent)
        }
      })

      this.cy.elements().hide()
      visible.show()
      node.addClass('highlighted')
      // Highlight direct neighbors
      const connected = node.connectedEdges()
      const neighbors = connected.connectedNodes()
      neighbors.addClass('highlighted')
      connected.addClass('highlighted')

      // Re-layout just the visible elements so they're compact
      visible.layout({
        name: 'dagre',
        rankDir: 'LR',
        nodeSep: 30,
        rankSep: 60,
        animate: true,
        animationDuration: 300,
        fit: true,
        padding: 40,
      }).run()

      // Emit all component node IDs for list highlighting
      const relatedIds = new Set()
      component.nodes().forEach(n => relatedIds.add(n.id()))
      this.$emit('related-nodes', relatedIds)

      // Build edge info
      if (data.nodeType === 'serviceaccount') {
        this.selectedEdges = connected.map(e => ({
          id: e.id(),
          label: e.data('label'),
          edgeType: e.data('edgeType'),
          targetLabel: e.target().data('label'),
          sourceLabel: e.source().data('label'),
        }))
      } else if (data.nodeType === 'role' || data.nodeType === 'clusterrole') {
        this.selectedEdges = connected.map(e => ({
          id: e.id(),
          label: e.data('label'),
          edgeType: e.data('edgeType'),
          sourceLabel: e.source().data('label'),
          targetLabel: e.target().data('label'),
        }))
      } else if (data.nodeType === 'namespace') {
        const children = node.children()
        this.selectedChildren = {
          serviceaccounts: children.filter('[nodeType="serviceaccount"]').length,
          roles: children.filter('[nodeType="role"]').length,
        }
        this.selectedEdges = []
        // Show namespace + children + their edges
        const childEdges = children.connectedEdges()
        const edgeNeighbors = childEdges.connectedNodes()
        const nsVisible = node.union(children).union(childEdges).union(edgeNeighbors)
        this.cy.elements().hide()
        nsVisible.show()
        children.addClass('highlighted')
      }
    },

    clearSelection() {
      this.selected = null
      this.selectedEdges = []
      this.$emit('node-selected', null)
      this.$emit('related-nodes', new Set())
      if (this.cy) {
        this.cy.elements().show()
        this.cy.elements().removeClass('highlighted')
        this.runLayout()
      }
    },

    describeRule(rule) {
      const verbs = (rule.verbs || []).join(', ')
      const resources = (rule.resources || []).join(', ')
      const groups = (rule.apiGroups || []).map(g => g === '' ? 'core' : g).join(', ')
      if (verbs === '*' && resources === '*') return `Full access (${groups})`
      const verbStr = verbs === '*' ? 'All operations' : `Can ${verbs}`
      return `${verbStr} on ${resources} (${groups})`
    },
  },
}
</script>
