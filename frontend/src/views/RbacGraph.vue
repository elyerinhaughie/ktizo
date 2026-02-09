<template>
  <div class="relative" ref="wrapper">
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
        <option value="dagre">Hierarchical</option>
        <option value="fcose">Clustered</option>
        <option value="cose">Force-directed</option>
        <option value="concentric">Concentric</option>
        <option value="breadthfirst">Tree</option>
        <option value="circle">Circle</option>
      </select>
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
/**
 * @component RbacGraph
 * @description Interactive Cytoscape.js graph visualization of Kubernetes RBAC relationships.
 *
 * Renders ServiceAccounts, Roles, ClusterRoles as nodes and RoleBindings/ClusterRoleBindings
 * as directed edges. Namespace nodes act as compound parents to visually group resources.
 *
 * Features:
 *   - Dagre (hierarchical left-to-right) and CoSE (force-directed) layout algorithms
 *   - Click-to-select with connected component isolation (hides unrelated nodes)
 *   - Detail side panel showing bound roles/rules/namespace contents
 *   - Responsive resizing via ResizeObserver
 *   - Dynamic theme adaptation via MutationObserver on `data-theme` attribute
 *   - Bidirectional focus sync with parent via focusNodeId prop and node-selected emit
 */
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import fcose from 'cytoscape-fcose'
import { buildElements } from '../services/rbacGraphBuilder'

// Register layout extensions with Cytoscape
cytoscape.use(dagre)
cytoscape.use(fcose)

/**
 * Color palette for each RBAC node type.
 * @type {Object<string, {bg: string, border: string, text: string}>}
 */
const NODE_COLORS = {
  serviceaccount: { bg: '#3b82f6', border: '#2563eb', text: '#ffffff' },
  role:           { bg: '#8b5cf6', border: '#7c3aed', text: '#ffffff' },
  clusterrole:    { bg: '#f59e0b', border: '#d97706', text: '#ffffff' },
  namespace:      { bg: '#e5e7eb', border: '#9ca3af', text: '#374151' },
}

/**
 * Cytoscape shape mapping for each RBAC node type.
 * Distinct shapes help differentiate node types at a glance.
 * @type {Object<string, string>}
 */
const NODE_SHAPES = {
  serviceaccount: 'round-rectangle',
  role:           'rectangle',
  clusterrole:    'diamond',
  namespace:      'ellipse',
}

export default {
  name: 'RbacGraph',

  /**
   * @prop {Array<Object>} serviceAccounts - Kubernetes ServiceAccount objects
   * @prop {Array<Object>} roles - Kubernetes Role objects
   * @prop {Array<Object>} clusterRoles - Kubernetes ClusterRole objects
   * @prop {Array<Object>} roleBindings - Kubernetes RoleBinding objects
   * @prop {Array<Object>} clusterRoleBindings - Kubernetes ClusterRoleBinding objects
   * @prop {boolean} showSystem - Whether to include system/built-in resources
   * @prop {string|null} focusNodeId - Node ID to programmatically select and zoom to
   */
  props: {
    serviceAccounts: { type: Array, default: () => [] },
    roles: { type: Array, default: () => [] },
    clusterRoles: { type: Array, default: () => [] },
    roleBindings: { type: Array, default: () => [] },
    clusterRoleBindings: { type: Array, default: () => [] },
    showSystem: { type: Boolean, default: false },
    focusNodeId: { type: String, default: null },
  },

  /**
   * @emits node-selected - Fired with the selected node's ID (or null on deselect)
   * @emits related-nodes - Fired with a Set of node IDs in the selected node's connected component
   */
  emits: ['node-selected', 'related-nodes'],

  data() {
    return {
      /** @type {cytoscape.Core|null} The Cytoscape.js instance */
      cy: null,
      /** @type {'dagre'|'fcose'|'cose'|'concentric'|'breadthfirst'|'circle'} Current layout algorithm name */
      layoutName: 'fcose',
      /** @type {Object|null} Data object of the currently selected node */
      selected: null,
      /** @type {Array<Object>} Edge metadata for the selected node's connections */
      selectedEdges: [],
      /** @type {{serviceaccounts: number, roles: number}} Child counts when a namespace is selected */
      selectedChildren: { serviceaccounts: 0, roles: 0 },
      /** @type {boolean} True when the graph has no elements to display */
      isEmpty: false,
      /** @type {ResizeObserver|null} Watches container size changes to resize the canvas */
      resizeObserver: null,
      /** @type {MutationObserver|null} Watches data-theme attribute for dark/light mode switches */
      themeObserver: null,
    }
  },

  computed: {
    /**
     * Human-readable label for the selected node's Kubernetes kind.
     * @returns {string}
     */
    selectedTypeLabel() {
      if (!this.selected) return ''
      return { serviceaccount: 'ServiceAccount', role: 'Role', clusterrole: 'ClusterRole', namespace: 'Namespace' }[this.selected.nodeType] || ''
    },

    /**
     * Tailwind CSS classes for the selected node's type badge.
     * @returns {string}
     */
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
    // Rebuild the graph whenever any RBAC data prop changes
    serviceAccounts() { this.rebuild() },
    roles() { this.rebuild() },
    clusterRoles() { this.rebuild() },
    roleBindings() { this.rebuild() },
    clusterRoleBindings() { this.rebuild() },
    showSystem() { this.rebuild() },

    /**
     * Responds to external focus requests (e.g., clicking a list item in the parent).
     * Null clears the selection; a valid ID triggers focus+select.
     */
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

    // Keep the Cytoscape canvas sized to its container
    this.resizeObserver = new ResizeObserver(() => {
      if (this.cy) {
        this.cy.resize()
        this.cy.fit(undefined, 30)
      }
    })
    this.resizeObserver.observe(this.$refs.cyContainer)

    // Re-apply styles when the app theme changes (dark/light mode toggle).
    // The MutationObserver watches for changes to the `data-theme` attribute
    // on <html>, which triggers a full stylesheet rebuild with updated CSS custom properties.
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
    /**
     * Creates the Cytoscape.js instance with initial configuration and event handlers.
     * Uses 'preset' layout initially (no positions) since rebuild() runs layout after adding elements.
     */
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

      // Select node on tap
      this.cy.on('tap', 'node', (evt) => {
        const node = evt.target
        this.selectNode(node)
      })

      // Clear selection when tapping empty canvas
      this.cy.on('tap', (evt) => {
        if (evt.target === this.cy) {
          this.clearSelection()
        }
      })
    },

    /**
     * Builds the complete Cytoscape stylesheet array.
     * Reads current CSS custom properties for theme-aware colors (namespace fills,
     * edge labels, canvas background for text outlines).
     * @returns {Array<Object>} Cytoscape style definitions
     */
    buildStylesheet() {
      const colors = this.getThemeColors()
      const styles = [
        // Base node style -- shared defaults for all node types
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
        // Compound (namespace) nodes -- dashed border, semi-transparent background,
        // label pinned to top center, extra padding for child nodes
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

      // Generate per-type styles from the NODE_COLORS/NODE_SHAPES maps
      for (const [type, color] of Object.entries(NODE_COLORS)) {
        if (type === 'namespace') continue // namespace handled above as compound node
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

      // Edge styles -- green for RoleBindings, teal dashed for ClusterRoleBindings
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
            'text-outline-color': colors.canvasBg, // match canvas bg so label text is readable
            'opacity': 0.7,
          },
        },
        // ClusterRoleBinding edges are visually distinct with dashed teal lines
        {
          selector: 'edge[edgeType="clusterrolebinding"]',
          style: {
            'line-style': 'dashed',
            'line-color': '#14b8a6',
            'target-arrow-color': '#14b8a6',
          },
        },
        // Highlighted state for selected node and its direct neighbors
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

    /**
     * Reads CSS custom properties from the document root to derive theme-aware colors.
     * Falls back to light-mode defaults when custom properties are not set.
     * @returns {Object} Theme color tokens for namespace, edges, and canvas
     */
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

    /**
     * Re-applies the stylesheet to the live Cytoscape instance.
     * Called when the theme changes to pick up new CSS custom property values.
     */
    applyStyles() {
      if (!this.cy) return
      this.cy.style(this.buildStylesheet())
    },

    /**
     * Rebuilds the entire graph from current prop data.
     * Clears all existing elements, re-transforms the RBAC data via buildElements(),
     * adds the new nodes/edges, and runs the layout algorithm.
     */
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

    /**
     * Executes the current layout algorithm on all graph elements.
     * Supports multiple layout algorithms suited to different graph sizes and structures.
     */
    runLayout() {
      if (!this.cy || this.cy.nodes().length === 0) return

      const layoutConfigs = {
        dagre: {
          name: 'dagre',
          rankDir: 'LR',
          nodeSep: 40,
          rankSep: 80,
          edgeSep: 20,
          animate: true,
          animationDuration: 300,
          fit: true,
          padding: 30,
        },
        fcose: {
          name: 'fcose',
          quality: 'default',
          animate: true,
          animationDuration: 300,
          fit: true,
          padding: 30,
          nodeSeparation: 75,
          idealEdgeLength: 100,
          nodeRepulsion: 4500,
          edgeElasticity: 0.45,
          gravity: 0.25,
          gravityRange: 3.8,
          nestingFactor: 0.1,
          numIter: 2500,
          tile: true,
          tilingPaddingVertical: 10,
          tilingPaddingHorizontal: 10,
        },
        cose: {
          name: 'cose',
          animate: true,
          animationDuration: 300,
          fit: true,
          padding: 30,
          nodeRepulsion: 8000,
          idealEdgeLength: 120,
          edgeElasticity: 100,
          gravity: 0.25,
        },
        concentric: {
          name: 'concentric',
          animate: true,
          animationDuration: 300,
          fit: true,
          padding: 30,
          minNodeSpacing: 40,
          concentric: (node) => node.connectedEdges().length,
          levelWidth: () => 2,
        },
        breadthfirst: {
          name: 'breadthfirst',
          directed: true,
          animate: true,
          animationDuration: 300,
          fit: true,
          padding: 30,
          spacingFactor: 1.2,
          circle: false,
        },
        circle: {
          name: 'circle',
          animate: true,
          animationDuration: 300,
          fit: true,
          padding: 30,
          spacingFactor: 1.5,
        },
      }

      this.cy.layout(layoutConfigs[this.layoutName] || layoutConfigs.fcose).run()
    },

    /**
     * Fits the entire graph into the viewport with 30px padding.
     */
    fitGraph() {
      if (this.cy) this.cy.fit(undefined, 30)
    },

    /**
     * Programmatically selects a node by its ID string.
     * Called when the parent component sets focusNodeId.
     * @param {string} nodeId - Cytoscape node ID (e.g., "sa:default/my-sa")
     */
    focusOnNode(nodeId) {
      if (!this.cy) return
      const node = this.cy.getElementById(nodeId)
      if (!node || node.length === 0) return

      this.selectNode(node)
    },

    /**
     * Handles node selection: isolates the connected component, highlights direct
     * neighbors, re-layouts the visible subgraph, and populates the detail panel.
     *
     * The selection flow:
     *   1. Find the full connected component (all reachable nodes via edges)
     *   2. Include parent namespace nodes so compound grouping is preserved
     *   3. Hide all other elements and re-layout only the visible subgraph
     *   4. Highlight the selected node and its direct neighbors/edges
     *   5. Emit component node IDs so the parent list can highlight related items
     *   6. Build detail panel data (edges for SA/Role, child counts for Namespace)
     *
     * @param {cytoscape.NodeSingular} node - The Cytoscape node element that was selected
     */
    selectNode(node) {
      this.cy.elements().removeClass('highlighted dimmed')

      const data = node.data()
      this.selected = data
      this.$emit('node-selected', node.id())

      // Traverse the full connected component -- all nodes reachable by any path from this node.
      // This ensures we show the complete relationship context, not just direct neighbors.
      const component = node.component()
      let visible = component

      // Compound nodes (namespaces) are not connected by edges, so they aren't part
      // of the component. We must explicitly include them to preserve visual grouping.
      visible.nodes().forEach(n => {
        const parent = n.parent()
        if (parent && parent.length > 0) {
          visible = visible.union(parent)
        }
      })

      // Isolate: hide everything, then show only the connected subgraph
      this.cy.elements().hide()
      visible.show()
      node.addClass('highlighted')

      // Highlight direct neighbors (one hop) more prominently than the rest of the component
      const connected = node.connectedEdges()
      const neighbors = connected.connectedNodes()
      neighbors.addClass('highlighted')
      connected.addClass('highlighted')

      // Re-layout just the visible elements for a compact, readable subgraph
      visible.layout({
        name: 'dagre', rankDir: 'LR', nodeSep: 30, rankSep: 60,
        animate: true, animationDuration: 300, fit: true, padding: 40,
      }).run()

      // Emit related node IDs so the parent can highlight matching list items
      const relatedIds = new Set()
      component.nodes().forEach(n => relatedIds.add(n.id()))
      this.$emit('related-nodes', relatedIds)

      // Build edge metadata for the detail panel based on selected node type
      if (data.nodeType === 'serviceaccount') {
        // For SAs, show which roles they're bound to
        this.selectedEdges = connected.map(e => ({
          id: e.id(),
          label: e.data('label'),
          edgeType: e.data('edgeType'),
          targetLabel: e.target().data('label'),
          sourceLabel: e.source().data('label'),
        }))
      } else if (data.nodeType === 'role' || data.nodeType === 'clusterrole') {
        // For roles, show which SAs are bound to them
        this.selectedEdges = connected.map(e => ({
          id: e.id(),
          label: e.data('label'),
          edgeType: e.data('edgeType'),
          sourceLabel: e.source().data('label'),
          targetLabel: e.target().data('label'),
        }))
      } else if (data.nodeType === 'namespace') {
        // For namespaces, count children by type and show the namespace's entire subgraph
        const children = node.children()
        this.selectedChildren = {
          serviceaccounts: children.filter('[nodeType="serviceaccount"]').length,
          roles: children.filter('[nodeType="role"]').length,
        }
        this.selectedEdges = []
        // Expand visible set to include children's edges and the nodes those edges connect to
        const childEdges = children.connectedEdges()
        const edgeNeighbors = childEdges.connectedNodes()
        const nsVisible = node.union(children).union(childEdges).union(edgeNeighbors)
        this.cy.elements().hide()
        nsVisible.show()
        children.addClass('highlighted')
      }
    },

    /**
     * Clears the current selection, restores all hidden elements, removes
     * highlights, and re-runs the layout to return to the full-graph view.
     */
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

    /**
     * Converts a Kubernetes RBAC rule object into a human-readable description.
     * @param {Object} rule - Rule with {verbs, resources, apiGroups} arrays
     * @returns {string} e.g., "Can get, list on pods (core)" or "Full access (apps)"
     */
    describeRule(rule) {
      const verbs = (rule.verbs || []).join(', ')
      const resources = (rule.resources || []).join(', ')
      // Map empty string API group to "core" for readability
      const groups = (rule.apiGroups || []).map(g => g === '' ? 'core' : g).join(', ')
      if (verbs === '*' && resources === '*') return `Full access (${groups})`
      const verbStr = verbs === '*' ? 'All operations' : `Can ${verbs}`
      return `${verbStr} on ${resources} (${groups})`
    },
  },
}
</script>
