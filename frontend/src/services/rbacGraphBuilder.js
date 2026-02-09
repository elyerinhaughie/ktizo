/**
 * @module rbacGraphBuilder
 * @description Transforms Kubernetes RBAC API data into Cytoscape.js graph elements.
 *
 * This service converts flat lists of K8s RBAC resources (ServiceAccounts, Roles,
 * ClusterRoles, RoleBindings, ClusterRoleBindings) into a graph structure of nodes
 * and edges suitable for Cytoscape.js rendering.
 *
 * Node ID conventions:
 *   - Namespace:      "ns:{name}"
 *   - ServiceAccount: "sa:{namespace}/{name}"
 *   - Role:           "role:{namespace}/{name}"
 *   - ClusterRole:    "clusterrole:{name}"
 *
 * Edge ID conventions:
 *   - RoleBinding:        "rb:{namespace}/{bindingName}:{subjectName}"
 *   - ClusterRoleBinding: "crb:{bindingName}:{namespace}/{subjectName}"
 *
 * Namespace nodes act as Cytoscape compound (parent) nodes, visually grouping
 * the ServiceAccounts and Roles that belong to them.
 */

/**
 * Builds Cytoscape.js elements from raw Kubernetes RBAC resources.
 *
 * The function performs three passes:
 *   1. Creates nodes for namespaces, ServiceAccounts, Roles, and ClusterRoles.
 *   2. Processes RoleBindings to create edges from subjects to their referenced roles,
 *      lazily creating any missing subject or role nodes encountered in bindings.
 *   3. Processes ClusterRoleBindings the same way.
 *
 * @param {Array<Object>} serviceAccounts - K8s ServiceAccount objects with {name, namespace}
 * @param {Array<Object>} roles - K8s Role objects with {name, namespace, rules}
 * @param {Array<Object>} clusterRoles - K8s ClusterRole objects with {name, rules}
 * @param {Array<Object>} roleBindings - K8s RoleBinding objects with {name, namespace, role_ref, subjects}
 * @param {Array<Object>} clusterRoleBindings - K8s ClusterRoleBinding objects with {name, role_ref, subjects}
 * @returns {{ nodes: Array<{data: Object}>, edges: Array<{data: Object}> }} Cytoscape elements
 */
export function buildElements(serviceAccounts, roles, clusterRoles, roleBindings, clusterRoleBindings) {
  const nodes = []
  const edges = []
  /** @type {Set<string>} Tracks added node IDs to prevent duplicates */
  const nodeSet = new Set()

  /**
   * Adds a node to the graph if it hasn't been added already.
   * @param {string} id - Unique node identifier (e.g., "sa:default/my-sa")
   * @param {Object} data - Cytoscape node data properties (label, nodeType, etc.)
   */
  function addNode(id, data) {
    if (nodeSet.has(id)) return
    nodeSet.add(id)
    nodes.push({ data: { id, ...data } })
  }

  // --- Pass 1: Collect namespaces from all namespace-scoped resources ---
  // These become compound (parent) nodes in Cytoscape for visual grouping.
  const namespaces = new Set()
  serviceAccounts.forEach(sa => { if (sa.namespace) namespaces.add(sa.namespace) })
  roles.forEach(r => { if (r.namespace) namespaces.add(r.namespace) })
  roleBindings.forEach(rb => { if (rb.namespace) namespaces.add(rb.namespace) })

  namespaces.forEach(ns => {
    addNode(`ns:${ns}`, { label: ns, nodeType: 'namespace' })
  })

  // ServiceAccount nodes -- parented to their namespace
  serviceAccounts.forEach(sa => {
    const id = `sa:${sa.namespace}/${sa.name}`
    addNode(id, {
      label: sa.name,
      nodeType: 'serviceaccount',
      namespace: sa.namespace,
      parent: `ns:${sa.namespace}`,
      raw: sa,
    })
  })

  // Role nodes -- namespace-scoped, parented to their namespace
  roles.forEach(r => {
    const id = `role:${r.namespace}/${r.name}`
    addNode(id, {
      label: r.name,
      nodeType: 'role',
      namespace: r.namespace,
      ruleCount: r.rules ? r.rules.length : 0,
      parent: `ns:${r.namespace}`,
      raw: r,
    })
  })

  // ClusterRole nodes -- cluster-scoped, no parent namespace
  clusterRoles.forEach(cr => {
    const id = `clusterrole:${cr.name}`
    addNode(id, {
      label: cr.name,
      nodeType: 'clusterrole',
      ruleCount: cr.rules ? cr.rules.length : 0,
      raw: cr,
    })
  })

  // --- Pass 2: RoleBindings create edges from subject -> role ---
  // A RoleBinding can reference either a Role or a ClusterRole.
  roleBindings.forEach(rb => {
    // Resolve the target role ID based on whether the binding references a Role or ClusterRole
    const roleId = rb.role_ref.kind === 'ClusterRole'
      ? `clusterrole:${rb.role_ref.name}`
      : `role:${rb.namespace}/${rb.role_ref.name}`

    // Lazily create the target role node if it wasn't in the initial roles/clusterRoles lists.
    // This can happen when a binding references a role the user doesn't have permission to list.
    if (!nodeSet.has(roleId)) {
      if (rb.role_ref.kind === 'ClusterRole') {
        addNode(roleId, { label: rb.role_ref.name, nodeType: 'clusterrole', ruleCount: 0 })
      } else {
        addNode(roleId, {
          label: rb.role_ref.name, nodeType: 'role', namespace: rb.namespace,
          ruleCount: 0, parent: `ns:${rb.namespace}`,
        })
      }
    }

    // Create an edge for each ServiceAccount subject in this binding
    ;(rb.subjects || []).forEach(subject => {
      if (subject.kind === 'ServiceAccount') {
        // Subject namespace falls back to the binding's namespace
        const ns = subject.namespace || rb.namespace
        const saId = `sa:${ns}/${subject.name}`
        // Lazily create subject node and its namespace parent if missing
        if (!nodeSet.has(saId)) {
          if (ns && !nodeSet.has(`ns:${ns}`)) {
            addNode(`ns:${ns}`, { label: ns, nodeType: 'namespace' })
          }
          addNode(saId, {
            label: subject.name, nodeType: 'serviceaccount',
            namespace: ns, parent: `ns:${ns}`,
          })
        }
        edges.push({
          data: {
            id: `rb:${rb.namespace}/${rb.name}:${subject.name}`,
            source: saId,
            target: roleId,
            label: rb.name,
            edgeType: 'rolebinding',
            namespace: rb.namespace,
          },
        })
      }
    })
  })

  // --- Pass 3: ClusterRoleBindings create edges from subject -> clusterrole ---
  // These always reference ClusterRoles and are cluster-scoped.
  clusterRoleBindings.forEach(crb => {
    const roleId = `clusterrole:${crb.role_ref.name}`
    if (!nodeSet.has(roleId)) {
      addNode(roleId, { label: crb.role_ref.name, nodeType: 'clusterrole', ruleCount: 0 })
    }

    ;(crb.subjects || []).forEach(subject => {
      if (subject.kind === 'ServiceAccount') {
        // Default to 'default' namespace when subject namespace is unspecified
        const ns = subject.namespace || 'default'
        const saId = `sa:${ns}/${subject.name}`
        if (!nodeSet.has(saId)) {
          if (!nodeSet.has(`ns:${ns}`)) {
            addNode(`ns:${ns}`, { label: ns, nodeType: 'namespace' })
          }
          addNode(saId, {
            label: subject.name, nodeType: 'serviceaccount',
            namespace: ns, parent: `ns:${ns}`,
          })
        }
        edges.push({
          data: {
            id: `crb:${crb.name}:${ns}/${subject.name}`,
            source: saId,
            target: roleId,
            label: crb.name,
            edgeType: 'clusterrolebinding',
          },
        })
      }
    })
  })

  return { nodes, edges }
}
