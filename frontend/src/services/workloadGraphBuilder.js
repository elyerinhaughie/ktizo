/**
 * @module workloadGraphBuilder
 * Transforms Kubernetes workload API data into Cytoscape.js graph elements.
 *
 * Node ID conventions:
 *   Namespace:    "ns:{name}"
 *   Deployment:   "deploy:{ns}/{name}"
 *   StatefulSet:  "sts:{ns}/{name}"
 *   DaemonSet:    "ds:{ns}/{name}"
 *   ReplicaSet:   "rs:{ns}/{name}"
 *   Pod:          "pod:{ns}/{name}"
 *   Service:      "svc:{ns}/{name}"
 *   Ingress:      "ing:{ns}/{name}"
 *   ConfigMap:    "cm:{ns}/{name}"
 *   Secret:       "sec:{ns}/{name}"
 *   PVC:          "pvc:{ns}/{name}"
 *
 * Relationship inference:
 *   1. OwnerReferences  — RS→Deploy, Pod→RS/STS/DS
 *   2. Label selectors  — Service→Pod
 *   3. Ingress rules    — Ingress→Service
 *   4. Volume/envFrom   — Pod→ConfigMap/Secret/PVC
 *   5. ServiceAccount   — Pod→SA (non-default only)
 */

/**
 * Build Cytoscape.js elements from workload API data.
 * @param {Object} data - Response from workloads.list
 * @returns {{ nodes: Array, edges: Array }}
 */
export function buildWorkloadElements(data) {
  const nodes = []
  const edges = []
  const nodeSet = new Set()
  const edgeSet = new Set()

  function addNode(id, nodeData) {
    if (nodeSet.has(id)) return
    nodeSet.add(id)
    nodes.push({ data: { id, ...nodeData } })
  }

  function addEdge(id, source, target, edgeData) {
    if (edgeSet.has(id)) return
    if (!nodeSet.has(source) || !nodeSet.has(target)) return
    edgeSet.add(id)
    edges.push({ data: { id, source, target, ...edgeData } })
  }

  const {
    namespaces = [], deployments = [], statefulsets = [], daemonsets = [],
    replicasets = [], pods = [], services = [], ingresses = [],
    configmaps = [], secrets = [], pvcs = [],
  } = data || {}

  // UID → node ID lookup for ownerReference resolution
  const uidToNodeId = new Map()
  // UID → kind, for determining compound parent types
  const uidToKind = new Map()

  // --- Pre-pass: Build ownership map from ownerReferences ---
  // Maps child UID → owner UID so we can nest children inside controller compound nodes.
  // Controllers (Deploy, STS, DS) become compound parents; RS nests inside Deploy;
  // Pods nest inside their nearest controller ancestor.
  const ownerUidMap = new Map() // childUid → ownerUid

  replicasets.forEach(rs => {
    ;(rs.owner_references || []).forEach(ref => { ownerUidMap.set(rs.uid, ref.uid) })
  })
  pods.forEach(pod => {
    ;(pod.owner_references || []).forEach(ref => { ownerUidMap.set(pod.uid, ref.uid) })
  })

  // Register all controller UIDs + kinds so we know which are compound-eligible
  const controllerKinds = new Set(['Deployment', 'StatefulSet', 'DaemonSet'])
  deployments.forEach(d => { uidToKind.set(d.uid, 'Deployment') })
  statefulsets.forEach(s => { uidToKind.set(s.uid, 'StatefulSet') })
  daemonsets.forEach(d => { uidToKind.set(d.uid, 'DaemonSet') })
  replicasets.forEach(rs => { uidToKind.set(rs.uid, 'ReplicaSet') })

  // --- Pass 1: Namespace compound nodes ---
  const allNamespaces = new Set()
  ;[deployments, statefulsets, daemonsets, replicasets, pods, services, ingresses, configmaps, secrets, pvcs]
    .forEach(list => list.forEach(r => { if (r.namespace) allNamespaces.add(r.namespace) }))

  allNamespaces.forEach(ns => {
    addNode(`ns:${ns}`, { label: ns, nodeType: 'namespace' })
  })

  // Helper: resolve the compound parent for a resource given its UID.
  // Returns the immediate owner's node ID (RS, controller, etc.) or falls back to namespace.
  function resolveParent(uid, namespace) {
    const ownerUid = ownerUidMap.get(uid)
    if (!ownerUid) return `ns:${namespace}`

    const ownerKind = uidToKind.get(ownerUid)
    // If owner is a controller (Deploy/STS/DS), parent to it
    if (ownerKind && controllerKinds.has(ownerKind)) {
      const parentId = uidToNodeId.get(ownerUid)
      return parentId || `ns:${namespace}`
    }
    // If owner is a ReplicaSet, nest inside the RS (RS itself nests inside Deploy)
    if (ownerKind === 'ReplicaSet') {
      const rsId = uidToNodeId.get(ownerUid)
      return rsId || `ns:${namespace}`
    }
    return `ns:${namespace}`
  }

  // --- Pass 2: Controller nodes (compound parents) ---
  // These must be created first so child nodes can reference them as parents.
  deployments.forEach(d => {
    const id = `deploy:${d.namespace}/${d.name}`
    uidToNodeId.set(d.uid, id)
    addNode(id, {
      label: `${d.name}\n(deployment)`, nodeType: 'deployment', namespace: d.namespace,
      parent: `ns:${d.namespace}`,
      replicas: d.replicas, readyReplicas: d.ready_replicas,
      raw: d,
    })
  })

  statefulsets.forEach(s => {
    const id = `sts:${s.namespace}/${s.name}`
    uidToNodeId.set(s.uid, id)
    addNode(id, {
      label: `${s.name}\n(statefulset)`, nodeType: 'statefulset', namespace: s.namespace,
      parent: `ns:${s.namespace}`,
      replicas: s.replicas, readyReplicas: s.ready_replicas,
      raw: s,
    })
  })

  daemonsets.forEach(d => {
    const id = `ds:${d.namespace}/${d.name}`
    uidToNodeId.set(d.uid, id)
    addNode(id, {
      label: `${d.name}\n(daemonset)`, nodeType: 'daemonset', namespace: d.namespace,
      parent: `ns:${d.namespace}`,
      desired: d.desired, ready: d.ready,
      raw: d,
    })
  })

  // --- Pass 2b: ReplicaSets — nest inside owning Deployment if present ---
  replicasets.forEach(rs => {
    const id = `rs:${rs.namespace}/${rs.name}`
    uidToNodeId.set(rs.uid, id)
    const parent = resolveParent(rs.uid, rs.namespace)
    addNode(id, {
      label: `${rs.name}\n(replicaset) ${rs.ready_replicas || 0}/${rs.replicas || 0}`, nodeType: 'replicaset', namespace: rs.namespace,
      parent,
      replicas: rs.replicas, readyReplicas: rs.ready_replicas,
      raw: rs,
    })
  })

  // --- Pass 2c: Pods — nest inside owning controller or RS ---
  pods.forEach(p => {
    const id = `pod:${p.namespace}/${p.name}`
    uidToNodeId.set(p.uid, id)
    const parent = resolveParent(p.uid, p.namespace)
    addNode(id, {
      label: `${p.name}\n(pod) ${p.phase || 'Unknown'}`, nodeType: 'pod', namespace: p.namespace,
      parent,
      phase: p.phase,
      raw: p,
    })
  })

  // --- Pass 2d: Remaining resource nodes (no compound nesting) ---
  services.forEach(s => {
    const id = `svc:${s.namespace}/${s.name}`
    uidToNodeId.set(s.uid, id)
    addNode(id, {
      label: `${s.name}\n(service)${s.cluster_ip ? '\nInternal: ' + s.cluster_ip : ''}${s.external_ips?.length ? '\nExternal: ' + s.external_ips.join(', ') : ''}`, nodeType: 'service', namespace: s.namespace,
      parent: `ns:${s.namespace}`,
      serviceType: s.type, ports: s.ports,
      raw: s,
    })
  })

  ingresses.forEach(i => {
    const id = `ing:${i.namespace}/${i.name}`
    uidToNodeId.set(i.uid, id)
    addNode(id, {
      label: `${i.name}\n(ingress)`, nodeType: 'ingress', namespace: i.namespace,
      parent: `ns:${i.namespace}`,
      raw: i,
    })
  })

  configmaps.forEach(cm => {
    const id = `cm:${cm.namespace}/${cm.name}`
    uidToNodeId.set(cm.uid, id)
    addNode(id, {
      label: `${cm.name}\n(configmap)`, nodeType: 'configmap', namespace: cm.namespace,
      parent: `ns:${cm.namespace}`,
      dataKeys: cm.data_keys,
      raw: cm,
    })
  })

  secrets.forEach(s => {
    const id = `sec:${s.namespace}/${s.name}`
    uidToNodeId.set(s.uid, id)
    addNode(id, {
      label: `${s.name}\n(secret)`, nodeType: 'secret', namespace: s.namespace,
      parent: `ns:${s.namespace}`,
      secretType: s.type, dataKeys: s.data_keys,
      raw: s,
    })
  })

  pvcs.forEach(p => {
    const id = `pvc:${p.namespace}/${p.name}`
    uidToNodeId.set(p.uid, id)
    addNode(id, {
      label: `${p.name}\n(pvc)`, nodeType: 'pvc', namespace: p.namespace,
      parent: `ns:${p.namespace}`,
      storageClass: p.storage_class, capacity: p.capacity, pvcPhase: p.phase,
      raw: p,
    })
  })

  // --- Pass 3: OwnerReference edges ---
  // Skip edges where the owner is a compound parent (controller or RS), since
  // compound nesting already shows that relationship visually.
  const compoundKinds = new Set([...controllerKinds, 'ReplicaSet'])

  replicasets.forEach(rs => {
    const rsId = `rs:${rs.namespace}/${rs.name}`
    ;(rs.owner_references || []).forEach(ref => {
      const parentId = uidToNodeId.get(ref.uid)
      if (!parentId) return
      const ownerKind = uidToKind.get(ref.uid)
      if (ownerKind && compoundKinds.has(ownerKind)) return
      addEdge(`owns:${parentId}->${rsId}`, parentId, rsId, {
        label: 'owns', edgeType: 'owns',
      })
    })
  })

  pods.forEach(pod => {
    const podId = `pod:${pod.namespace}/${pod.name}`
    ;(pod.owner_references || []).forEach(ref => {
      const parentId = uidToNodeId.get(ref.uid)
      if (!parentId) return
      const ownerKind = uidToKind.get(ref.uid)
      if (ownerKind && compoundKinds.has(ownerKind)) return
      addEdge(`owns:${parentId}->${podId}`, parentId, podId, {
        label: 'owns', edgeType: 'owns',
      })
    })
  })

  // --- Pass 4: Service → Pod edges (label selector matching) ---
  services.forEach(svc => {
    if (!svc.selector || Object.keys(svc.selector).length === 0) return
    const svcId = `svc:${svc.namespace}/${svc.name}`
    const selectorEntries = Object.entries(svc.selector)

    pods.forEach(pod => {
      if (pod.namespace !== svc.namespace) return
      if (!pod.labels) return
      const matches = selectorEntries.every(([k, v]) => pod.labels[k] === v)
      if (matches) {
        const podId = `pod:${pod.namespace}/${pod.name}`
        addEdge(`selects:${svcId}->${podId}`, svcId, podId, {
          label: 'selects', edgeType: 'selects',
        })
      }
    })
  })

  // --- Pass 5: Ingress → Service edges ---
  ingresses.forEach(ing => {
    const ingId = `ing:${ing.namespace}/${ing.name}`
    ;(ing.backends || []).forEach(backend => {
      if (!backend.service_name) return
      const svcId = `svc:${ing.namespace}/${backend.service_name}`
      if (nodeSet.has(svcId)) {
        const label = `${backend.host}${backend.path || '/'}`
        addEdge(`routes:${ingId}->${svcId}`, ingId, svcId, {
          label, edgeType: 'routes',
        })
      }
    })
  })

  // --- Pass 6: Pod → ConfigMap/Secret/PVC mount edges + ServiceAccount ---
  pods.forEach(pod => {
    const podId = `pod:${pod.namespace}/${pod.name}`
    const mountedTargets = new Set()

    // Volume mounts
    ;(pod.volumes || []).forEach(vol => {
      let targetId = null
      if (vol.type === 'configmap') targetId = `cm:${pod.namespace}/${vol.name}`
      else if (vol.type === 'secret') targetId = `sec:${pod.namespace}/${vol.name}`
      else if (vol.type === 'pvc') targetId = `pvc:${pod.namespace}/${vol.name}`

      if (targetId && nodeSet.has(targetId) && !mountedTargets.has(targetId)) {
        mountedTargets.add(targetId)
        addEdge(`mounts:${podId}->${targetId}`, podId, targetId, {
          label: 'mounts', edgeType: 'mounts',
        })
      }
    })

    // envFrom references (deduplicate against volume mounts)
    ;(pod.env_refs || []).forEach(ref => {
      let targetId = null
      if (ref.type === 'configmap') targetId = `cm:${pod.namespace}/${ref.name}`
      else if (ref.type === 'secret') targetId = `sec:${pod.namespace}/${ref.name}`

      if (targetId && nodeSet.has(targetId) && !mountedTargets.has(targetId)) {
        mountedTargets.add(targetId)
        addEdge(`envfrom:${podId}->${targetId}`, podId, targetId, {
          label: 'envFrom', edgeType: 'mounts',
        })
      }
    })

    // ServiceAccount (skip 'default' to reduce noise)
    if (pod.service_account_name && pod.service_account_name !== 'default') {
      const saId = `sa:${pod.namespace}/${pod.service_account_name}`
      // Only create edge if we happen to have the SA node (we don't fetch SAs in workloads)
      // We could lazily create the node:
      if (!nodeSet.has(saId)) {
        addNode(saId, {
          label: `${pod.service_account_name}\n(serviceaccount)`, nodeType: 'serviceaccount',
          namespace: pod.namespace, parent: `ns:${pod.namespace}`,
        })
      }
      addEdge(`usessa:${podId}->${saId}`, podId, saId, {
        label: 'uses SA', edgeType: 'usessa',
      })
    }
  })

  // --- Pass 7: Network zones + Internet node ---
  // Create an "External" zone with an Internet node. Ingresses and
  // LoadBalancer/NodePort Services get edges from the Internet node to
  // show external reachability.

  const hasIngresses = ingresses.length > 0
  const externalServices = services.filter(
    s => s.type === 'LoadBalancer' || s.type === 'NodePort'
  )
  const hasExternalAccess = hasIngresses || externalServices.length > 0

  if (hasExternalAccess) {
    addNode('zone:external', { label: 'External', nodeType: 'zone' })
    addNode('internet', {
      label: 'Internet', nodeType: 'internet', parent: 'zone:external',
    })

    // Internet → Ingress edges
    ingresses.forEach(ing => {
      const ingId = `ing:${ing.namespace}/${ing.name}`
      const hosts = (ing.backends || []).map(b => b.host).filter(h => h && h !== '*')
      const label = hosts.length > 0 ? hosts[0] : 'HTTPS'
      addEdge(`inet->:${ingId}`, 'internet', ingId, {
        label, edgeType: 'external',
      })
    })

    // Internet → LoadBalancer / NodePort Service edges
    externalServices.forEach(svc => {
      const svcId = `svc:${svc.namespace}/${svc.name}`
      const portStr = (svc.ports || []).map(p => p.port).join(', ')
      addEdge(`inet->:${svcId}`, 'internet', svcId, {
        label: `${svc.type}${portStr ? ' :' + portStr : ''}`, edgeType: 'external',
      })
    })
  }

  return { nodes, edges }
}
