"""Kubernetes workload resource WebSocket handlers.

Lists Deployments, StatefulSets, DaemonSets, ReplicaSets, Pods, Services,
Ingresses, ConfigMaps, Secrets, and PVCs for graph visualization.  All
relationship inference (ownerReferences, label selectors, volume mounts)
happens on the frontend — this handler is a pure data source.
"""
import asyncio
import logging
from pathlib import Path

from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)

_SYSTEM_NAMESPACES = frozenset({"kube-system", "kube-public", "kube-node-lease"})

_NO_CLUSTER = "Kubernetes cluster not configured. Generate cluster configs and bootstrap the cluster first."


# ---------------------------------------------------------------------------
# Kubernetes client helpers
# ---------------------------------------------------------------------------

def _get_workload_clients():
    """Return (CoreV1Api, AppsV1Api, NetworkingV1Api) or (None, None, None)."""
    try:
        from kubernetes import client, config
        kubeconfig = Path.home() / ".kube" / "config"
        if not kubeconfig.exists():
            return None, None, None
        config.load_kube_config(config_file=str(kubeconfig))
        return client.CoreV1Api(), client.AppsV1Api(), client.NetworkingV1Api()
    except Exception:
        return None, None, None


def _should_include_ns(namespace: str, include_system: bool) -> bool:
    if include_system:
        return True
    return namespace not in _SYSTEM_NAMESPACES


# ---------------------------------------------------------------------------
# Serializers — extract only graph-relevant fields
# ---------------------------------------------------------------------------

def _serialize_owner_refs(obj) -> list:
    """Extract ownerReferences as [{kind, name, uid}]."""
    refs = getattr(obj.metadata, "owner_references", None)
    if not refs:
        return []
    return [{"kind": r.kind, "name": r.name, "uid": r.uid} for r in refs]


def _serialize_deployment(dep) -> dict:
    spec = dep.spec
    status = dep.status or type("S", (), {"ready_replicas": None})()
    return {
        "name": dep.metadata.name,
        "namespace": dep.metadata.namespace,
        "uid": dep.metadata.uid,
        "labels": dict(dep.metadata.labels or {}),
        "selector": dict((spec.selector.match_labels or {}) if spec.selector else {}),
        "replicas": spec.replicas or 0,
        "ready_replicas": status.ready_replicas or 0,
        "creation_timestamp": dep.metadata.creation_timestamp.isoformat() if dep.metadata.creation_timestamp else None,
    }


def _serialize_statefulset(sts) -> dict:
    spec = sts.spec
    status = sts.status or type("S", (), {"ready_replicas": None})()
    return {
        "name": sts.metadata.name,
        "namespace": sts.metadata.namespace,
        "uid": sts.metadata.uid,
        "labels": dict(sts.metadata.labels or {}),
        "selector": dict((spec.selector.match_labels or {}) if spec.selector else {}),
        "replicas": spec.replicas or 0,
        "ready_replicas": status.ready_replicas or 0,
        "creation_timestamp": sts.metadata.creation_timestamp.isoformat() if sts.metadata.creation_timestamp else None,
    }


def _serialize_daemonset(ds) -> dict:
    status = ds.status or type("S", (), {"desired_number_scheduled": 0, "number_ready": 0})()
    spec = ds.spec
    return {
        "name": ds.metadata.name,
        "namespace": ds.metadata.namespace,
        "uid": ds.metadata.uid,
        "labels": dict(ds.metadata.labels or {}),
        "selector": dict((spec.selector.match_labels or {}) if spec.selector else {}),
        "desired": status.desired_number_scheduled or 0,
        "ready": status.number_ready or 0,
        "creation_timestamp": ds.metadata.creation_timestamp.isoformat() if ds.metadata.creation_timestamp else None,
    }


def _serialize_replicaset(rs) -> dict:
    spec = rs.spec
    status = rs.status or type("S", (), {"ready_replicas": None})()
    return {
        "name": rs.metadata.name,
        "namespace": rs.metadata.namespace,
        "uid": rs.metadata.uid,
        "owner_references": _serialize_owner_refs(rs),
        "replicas": spec.replicas if spec.replicas is not None else 0,
        "ready_replicas": status.ready_replicas or 0,
    }


def _serialize_pod(pod) -> dict:
    spec = pod.spec or type("S", (), {
        "volumes": None, "containers": None, "service_account_name": None,
    })()

    # Extract volume references
    volumes = []
    for v in (spec.volumes or []):
        if v.config_map:
            volumes.append({"type": "configmap", "name": v.config_map.name})
        elif v.secret:
            volumes.append({"type": "secret", "name": v.secret.secret_name})
        elif v.persistent_volume_claim:
            volumes.append({"type": "pvc", "name": v.persistent_volume_claim.claim_name})

    # Extract envFrom references
    env_refs = []
    for c in (spec.containers or []):
        for ef in (c.env_from or []):
            if ef.config_map_ref:
                env_refs.append({"type": "configmap", "name": ef.config_map_ref.name})
            elif ef.secret_ref:
                env_refs.append({"type": "secret", "name": ef.secret_ref.name})

    phase = "Unknown"
    if pod.status and pod.status.phase:
        phase = pod.status.phase

    return {
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "uid": pod.metadata.uid,
        "labels": dict(pod.metadata.labels or {}),
        "owner_references": _serialize_owner_refs(pod),
        "phase": phase,
        "service_account_name": spec.service_account_name,
        "volumes": volumes,
        "env_refs": env_refs,
    }


def _serialize_service(svc) -> dict:
    spec = svc.spec or type("S", (), {"selector": None, "type": "ClusterIP", "ports": None})()
    ports = []
    for p in (spec.ports or []):
        ports.append({
            "port": p.port,
            "target_port": str(p.target_port) if p.target_port else None,
            "protocol": p.protocol or "TCP",
            "name": p.name,
        })
    cluster_ip = getattr(spec, 'cluster_ip', None) or None
    external_ips = []
    status = svc.status
    if status and status.load_balancer and status.load_balancer.ingress:
        for lb in status.load_balancer.ingress:
            if lb.ip:
                external_ips.append(lb.ip)
            elif lb.hostname:
                external_ips.append(lb.hostname)

    return {
        "name": svc.metadata.name,
        "namespace": svc.metadata.namespace,
        "uid": svc.metadata.uid,
        "selector": dict(spec.selector or {}),
        "type": spec.type or "ClusterIP",
        "ports": ports,
        "cluster_ip": cluster_ip if cluster_ip != "None" else None,
        "external_ips": external_ips,
    }


def _serialize_ingress(ing) -> dict:
    backends = []
    spec = ing.spec
    if spec and spec.rules:
        for rule in spec.rules:
            host = rule.host or "*"
            if rule.http and rule.http.paths:
                for path_obj in rule.http.paths:
                    backend = path_obj.backend
                    svc_name = None
                    svc_port = None
                    if backend and backend.service:
                        svc_name = backend.service.name
                        if backend.service.port:
                            svc_port = backend.service.port.number or backend.service.port.name
                    backends.append({
                        "host": host,
                        "path": path_obj.path or "/",
                        "service_name": svc_name,
                        "service_port": svc_port,
                    })
    return {
        "name": ing.metadata.name,
        "namespace": ing.metadata.namespace,
        "uid": ing.metadata.uid,
        "backends": backends,
    }


def _serialize_configmap(cm) -> dict:
    return {
        "name": cm.metadata.name,
        "namespace": cm.metadata.namespace,
        "uid": cm.metadata.uid,
        "data_keys": list((cm.data or {}).keys()),
    }


def _serialize_secret(secret) -> dict:
    return {
        "name": secret.metadata.name,
        "namespace": secret.metadata.namespace,
        "uid": secret.metadata.uid,
        "type": secret.type or "Opaque",
        "data_keys": list((secret.data or {}).keys()),
    }


def _serialize_pvc(pvc) -> dict:
    spec = pvc.spec or type("S", (), {
        "storage_class_name": None, "access_modes": None,
    })()
    status = pvc.status or type("S", (), {"phase": "Unknown", "capacity": None})()
    capacity = None
    if status.capacity and "storage" in status.capacity:
        capacity = status.capacity["storage"]
    return {
        "name": pvc.metadata.name,
        "namespace": pvc.metadata.namespace,
        "uid": pvc.metadata.uid,
        "storage_class": spec.storage_class_name,
        "access_modes": list(spec.access_modes or []),
        "capacity": capacity,
        "phase": status.phase or "Unknown",
    }


# ---------------------------------------------------------------------------
# Sync list functions (blocking K8s API calls, run via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _list_namespaces_sync() -> list[str]:
    core_api, _, _ = _get_workload_clients()
    if core_api is None:
        return []
    try:
        ns_list = core_api.list_namespace()
        return [ns.metadata.name for ns in ns_list.items]
    except Exception as e:
        logger.error(f"Failed to list namespaces: {e}")
        return []


def _list_deployments_sync(namespace: str | None, include_system: bool) -> list[dict]:
    _, apps_api, _ = _get_workload_clients()
    if apps_api is None:
        return []
    try:
        if namespace:
            items = apps_api.list_namespaced_deployment(namespace)
        else:
            items = apps_api.list_deployment_for_all_namespaces()
        result = [_serialize_deployment(d) for d in items.items]
        if not include_system:
            result = [d for d in result if _should_include_ns(d["namespace"], False)]
        return result
    except Exception as e:
        logger.error(f"Failed to list deployments: {e}")
        return []


def _list_statefulsets_sync(namespace: str | None, include_system: bool) -> list[dict]:
    _, apps_api, _ = _get_workload_clients()
    if apps_api is None:
        return []
    try:
        if namespace:
            items = apps_api.list_namespaced_stateful_set(namespace)
        else:
            items = apps_api.list_stateful_set_for_all_namespaces()
        result = [_serialize_statefulset(s) for s in items.items]
        if not include_system:
            result = [s for s in result if _should_include_ns(s["namespace"], False)]
        return result
    except Exception as e:
        logger.error(f"Failed to list statefulsets: {e}")
        return []


def _list_daemonsets_sync(namespace: str | None, include_system: bool) -> list[dict]:
    _, apps_api, _ = _get_workload_clients()
    if apps_api is None:
        return []
    try:
        if namespace:
            items = apps_api.list_namespaced_daemon_set(namespace)
        else:
            items = apps_api.list_daemon_set_for_all_namespaces()
        result = [_serialize_daemonset(d) for d in items.items]
        if not include_system:
            result = [d for d in result if _should_include_ns(d["namespace"], False)]
        return result
    except Exception as e:
        logger.error(f"Failed to list daemonsets: {e}")
        return []


def _list_replicasets_sync(namespace: str | None, include_system: bool) -> list[dict]:
    _, apps_api, _ = _get_workload_clients()
    if apps_api is None:
        return []
    try:
        if namespace:
            items = apps_api.list_namespaced_replica_set(namespace)
        else:
            items = apps_api.list_replica_set_for_all_namespaces()
        result = [_serialize_replicaset(rs) for rs in items.items]
        # Skip old ReplicaSets with 0 replicas
        result = [rs for rs in result if rs["replicas"] > 0]
        if not include_system:
            result = [rs for rs in result if _should_include_ns(rs["namespace"], False)]
        return result
    except Exception as e:
        logger.error(f"Failed to list replicasets: {e}")
        return []


def _list_pods_sync(namespace: str | None, include_system: bool) -> list[dict]:
    core_api, _, _ = _get_workload_clients()
    if core_api is None:
        return []
    try:
        if namespace:
            items = core_api.list_namespaced_pod(namespace)
        else:
            items = core_api.list_pod_for_all_namespaces()
        result = [_serialize_pod(p) for p in items.items]
        if not include_system:
            result = [p for p in result if _should_include_ns(p["namespace"], False)]
        return result
    except Exception as e:
        logger.error(f"Failed to list pods: {e}")
        return []


def _list_services_sync(namespace: str | None, include_system: bool) -> list[dict]:
    core_api, _, _ = _get_workload_clients()
    if core_api is None:
        return []
    try:
        if namespace:
            items = core_api.list_namespaced_service(namespace)
        else:
            items = core_api.list_service_for_all_namespaces()
        result = [_serialize_service(s) for s in items.items]
        if not include_system:
            result = [s for s in result if _should_include_ns(s["namespace"], False)]
        return result
    except Exception as e:
        logger.error(f"Failed to list services: {e}")
        return []


def _list_ingresses_sync(namespace: str | None, include_system: bool) -> list[dict]:
    _, _, net_api = _get_workload_clients()
    if net_api is None:
        return []
    try:
        if namespace:
            items = net_api.list_namespaced_ingress(namespace)
        else:
            items = net_api.list_ingress_for_all_namespaces()
        result = [_serialize_ingress(i) for i in items.items]
        if not include_system:
            result = [i for i in result if _should_include_ns(i["namespace"], False)]
        return result
    except Exception as e:
        logger.error(f"Failed to list ingresses: {e}")
        return []


def _list_configmaps_sync(namespace: str | None, include_system: bool) -> list[dict]:
    core_api, _, _ = _get_workload_clients()
    if core_api is None:
        return []
    try:
        if namespace:
            items = core_api.list_namespaced_config_map(namespace)
        else:
            items = core_api.list_config_map_for_all_namespaces()
        result = [_serialize_configmap(cm) for cm in items.items]
        if not include_system:
            result = [cm for cm in result if _should_include_ns(cm["namespace"], False)]
        return result
    except Exception as e:
        logger.error(f"Failed to list configmaps: {e}")
        return []


def _list_secrets_sync(namespace: str | None, include_system: bool) -> list[dict]:
    core_api, _, _ = _get_workload_clients()
    if core_api is None:
        return []
    try:
        if namespace:
            items = core_api.list_namespaced_secret(namespace)
        else:
            items = core_api.list_secret_for_all_namespaces()
        result = [_serialize_secret(s) for s in items.items]
        if not include_system:
            result = [s for s in result if _should_include_ns(s["namespace"], False)]
        return result
    except Exception as e:
        logger.error(f"Failed to list secrets: {e}")
        return []


def _list_pvcs_sync(namespace: str | None, include_system: bool) -> list[dict]:
    core_api, _, _ = _get_workload_clients()
    if core_api is None:
        return []
    try:
        if namespace:
            items = core_api.list_namespaced_persistent_volume_claim(namespace)
        else:
            items = core_api.list_persistent_volume_claim_for_all_namespaces()
        result = [_serialize_pvc(p) for p in items.items]
        if not include_system:
            result = [p for p in result if _should_include_ns(p["namespace"], False)]
        return result
    except Exception as e:
        logger.error(f"Failed to list pvcs: {e}")
        return []


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------

async def _workloads_list(params: dict, ws: WebSocket, req_id: str):
    """Fetch all workload resources in parallel and return as a single payload."""
    ns = params.get("namespace") or None
    include_system = params.get("include_system", False)

    try:
        results = await asyncio.gather(
            asyncio.to_thread(_list_namespaces_sync),
            asyncio.to_thread(_list_deployments_sync, ns, include_system),
            asyncio.to_thread(_list_statefulsets_sync, ns, include_system),
            asyncio.to_thread(_list_daemonsets_sync, ns, include_system),
            asyncio.to_thread(_list_replicasets_sync, ns, include_system),
            asyncio.to_thread(_list_pods_sync, ns, include_system),
            asyncio.to_thread(_list_services_sync, ns, include_system),
            asyncio.to_thread(_list_ingresses_sync, ns, include_system),
            asyncio.to_thread(_list_configmaps_sync, ns, include_system),
            asyncio.to_thread(_list_secrets_sync, ns, include_system),
            asyncio.to_thread(_list_pvcs_sync, ns, include_system),
        )

        data = {
            "namespaces": results[0],
            "deployments": results[1],
            "statefulsets": results[2],
            "daemonsets": results[3],
            "replicasets": results[4],
            "pods": results[5],
            "services": results[6],
            "ingresses": results[7],
            "configmaps": results[8],
            "secrets": results[9],
            "pvcs": results[10],
        }
        await _ws._respond(ws, req_id, data)
    except Exception as e:
        logger.error(f"workloads.list error: {e}")
        await _ws._respond(ws, req_id, error=str(e))


# ---------------------------------------------------------------------------
# Action map
# ---------------------------------------------------------------------------

WORKLOAD_ACTIONS = {
    "workloads.list": _workloads_list,
}
