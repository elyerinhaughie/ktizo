/**
 * Transforms RBAC API data into Cytoscape.js elements (nodes + edges).
 */

export function buildElements(serviceAccounts, roles, clusterRoles, roleBindings, clusterRoleBindings) {
  const nodes = []
  const edges = []
  const nodeSet = new Set()

  function addNode(id, data) {
    if (nodeSet.has(id)) return
    nodeSet.add(id)
    nodes.push({ data: { id, ...data } })
  }

  // Collect namespaces for compound grouping
  const namespaces = new Set()
  serviceAccounts.forEach(sa => { if (sa.namespace) namespaces.add(sa.namespace) })
  roles.forEach(r => { if (r.namespace) namespaces.add(r.namespace) })
  roleBindings.forEach(rb => { if (rb.namespace) namespaces.add(rb.namespace) })

  namespaces.forEach(ns => {
    addNode(`ns:${ns}`, { label: ns, nodeType: 'namespace' })
  })

  // ServiceAccount nodes
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

  // Role nodes
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

  // ClusterRole nodes
  clusterRoles.forEach(cr => {
    const id = `clusterrole:${cr.name}`
    addNode(id, {
      label: cr.name,
      nodeType: 'clusterrole',
      ruleCount: cr.rules ? cr.rules.length : 0,
      raw: cr,
    })
  })

  // RoleBindings → edges
  roleBindings.forEach(rb => {
    const roleId = rb.role_ref.kind === 'ClusterRole'
      ? `clusterrole:${rb.role_ref.name}`
      : `role:${rb.namespace}/${rb.role_ref.name}`

    // Ensure target role node exists
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

    ;(rb.subjects || []).forEach(subject => {
      if (subject.kind === 'ServiceAccount') {
        const ns = subject.namespace || rb.namespace
        const saId = `sa:${ns}/${subject.name}`
        if (!nodeSet.has(saId)) {
          // Ensure namespace parent
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

  // ClusterRoleBindings → edges
  clusterRoleBindings.forEach(crb => {
    const roleId = `clusterrole:${crb.role_ref.name}`
    if (!nodeSet.has(roleId)) {
      addNode(roleId, { label: crb.role_ref.name, nodeType: 'clusterrole', ruleCount: 0 })
    }

    ;(crb.subjects || []).forEach(subject => {
      if (subject.kind === 'ServiceAccount') {
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
