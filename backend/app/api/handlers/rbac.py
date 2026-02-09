"""Kubernetes RBAC management WebSocket handlers.

Provides CRUD for ServiceAccounts, Roles, ClusterRoles, RoleBindings, and
ClusterRoleBindings.  Includes a wizard composite action that creates an
SA + Role + Binding in a single step, with preset role templates for
novice users.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hidden system prefixes (filtered out by default)
# ---------------------------------------------------------------------------

_HIDDEN_PREFIXES = ("system:", "kubeadm:", "calico-")


def _is_system(name: str) -> bool:
    return any(name.startswith(p) for p in _HIDDEN_PREFIXES)


def _should_include(name: str, include_system: bool) -> bool:
    if include_system:
        return True
    return not _is_system(name)


# ---------------------------------------------------------------------------
# Preset role templates
# ---------------------------------------------------------------------------

ROLE_PRESETS = {
    "namespace-admin": {
        "id": "namespace-admin",
        "label": "Namespace Admin",
        "description": "Full access to all resources within a namespace.",
        "explanation": "This role lets a user create, update, and delete any resource (pods, deployments, services, configmaps, secrets, etc.) inside a specific namespace. Think of it as 'project owner' for that namespace.",
        "scope": "namespace",
        "rules": [
            {
                "apiGroups": ["", "apps", "batch", "autoscaling", "networking.k8s.io", "policy"],
                "resources": ["*"],
                "verbs": ["*"],
            }
        ],
    },
    "read-only": {
        "id": "read-only",
        "label": "Read-Only Viewer",
        "description": "Can view all resources in a namespace but cannot modify anything.",
        "explanation": "This role lets a user see pods, deployments, services, logs, and other resources, but they cannot create, edit, or delete anything. Ideal for auditors or observers.",
        "scope": "namespace",
        "rules": [
            {
                "apiGroups": ["", "apps", "batch", "autoscaling", "networking.k8s.io"],
                "resources": ["*"],
                "verbs": ["get", "list", "watch"],
            }
        ],
    },
    "pod-manager": {
        "id": "pod-manager",
        "label": "Pod Manager",
        "description": "Can manage pods, view logs, and exec into containers.",
        "explanation": "This role is for operators who need to troubleshoot running workloads. They can view pods, read logs, exec into containers, and delete stuck pods, but they cannot deploy new applications.",
        "scope": "namespace",
        "rules": [
            {
                "apiGroups": [""],
                "resources": ["pods", "pods/log", "pods/exec", "pods/portforward"],
                "verbs": ["get", "list", "watch", "create", "delete"],
            },
            {
                "apiGroups": [""],
                "resources": ["events"],
                "verbs": ["get", "list", "watch"],
            },
        ],
    },
    "deployment-manager": {
        "id": "deployment-manager",
        "label": "Deployment Manager",
        "description": "Can manage deployments, services, configmaps, and secrets.",
        "explanation": "This role lets a user deploy applications, scale them, and expose them via services. They can also manage configmaps and secrets. This is the typical role for a developer or DevOps engineer.",
        "scope": "namespace",
        "rules": [
            {
                "apiGroups": ["apps"],
                "resources": ["deployments", "replicasets", "statefulsets", "daemonsets"],
                "verbs": ["*"],
            },
            {
                "apiGroups": [""],
                "resources": ["services", "configmaps", "secrets", "persistentvolumeclaims"],
                "verbs": ["*"],
            },
            {
                "apiGroups": [""],
                "resources": ["pods", "pods/log"],
                "verbs": ["get", "list", "watch"],
            },
            {
                "apiGroups": ["networking.k8s.io"],
                "resources": ["ingresses"],
                "verbs": ["*"],
            },
        ],
    },
    "secret-manager": {
        "id": "secret-manager",
        "label": "Secret Manager",
        "description": "Can manage secrets and configmaps in a namespace.",
        "explanation": "This role is for users who need to manage application configuration and credentials but should not be able to deploy or modify workloads directly.",
        "scope": "namespace",
        "rules": [
            {
                "apiGroups": [""],
                "resources": ["secrets", "configmaps"],
                "verbs": ["*"],
            },
        ],
    },
    "cluster-viewer": {
        "id": "cluster-viewer",
        "label": "Cluster-Wide Viewer",
        "description": "Can view resources across all namespaces. Read-only cluster-level access.",
        "explanation": "This ClusterRole lets a user see everything in every namespace, including nodes, persistent volumes, and namespaces themselves, but they cannot change anything. Useful for monitoring dashboards or cluster-wide auditors.",
        "scope": "cluster",
        "rules": [
            {
                "apiGroups": ["", "apps", "batch", "autoscaling", "networking.k8s.io", "rbac.authorization.k8s.io"],
                "resources": ["*"],
                "verbs": ["get", "list", "watch"],
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Kubernetes client helpers
# ---------------------------------------------------------------------------

def _get_rbac_clients():
    """Return ``(CoreV1Api, RbacAuthorizationV1Api)`` or ``(None, None)``."""
    try:
        from kubernetes import client, config

        kubeconfig = Path.home() / ".kube" / "config"
        if not kubeconfig.exists():
            return None, None
        config.load_kube_config(config_file=str(kubeconfig))
        return client.CoreV1Api(), client.RbacAuthorizationV1Api()
    except Exception:
        return None, None


_NO_CLUSTER = "Kubernetes cluster not configured. Generate cluster configs and bootstrap the cluster first."


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize_role(role) -> dict:
    return {
        "name": role.metadata.name,
        "namespace": getattr(role.metadata, "namespace", None),
        "creation_timestamp": role.metadata.creation_timestamp.isoformat() if role.metadata.creation_timestamp else None,
        "labels": dict(role.metadata.labels or {}),
        "is_system": _is_system(role.metadata.name),
        "rules": [
            {
                "apiGroups": list(r.api_groups or []),
                "resources": list(r.resources or []),
                "verbs": list(r.verbs or []),
                "resourceNames": list(r.resource_names or []) if r.resource_names else [],
            }
            for r in (role.rules or [])
        ],
    }


def _serialize_binding(binding) -> dict:
    return {
        "name": binding.metadata.name,
        "namespace": getattr(binding.metadata, "namespace", None),
        "creation_timestamp": binding.metadata.creation_timestamp.isoformat() if binding.metadata.creation_timestamp else None,
        "is_system": _is_system(binding.metadata.name),
        "role_ref": {
            "kind": binding.role_ref.kind,
            "name": binding.role_ref.name,
            "api_group": binding.role_ref.api_group,
        },
        "subjects": [
            {
                "kind": s.kind,
                "name": s.name,
                "namespace": getattr(s, "namespace", None),
            }
            for s in (binding.subjects or [])
        ],
    }


def _serialize_service_account(sa) -> dict:
    return {
        "name": sa.metadata.name,
        "namespace": sa.metadata.namespace,
        "creation_timestamp": sa.metadata.creation_timestamp.isoformat() if sa.metadata.creation_timestamp else None,
        "is_system": sa.metadata.name == "default" or _is_system(sa.metadata.name),
    }


# ---------------------------------------------------------------------------
# Sync helpers (run via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _list_namespaces_sync() -> list[str]:
    core_api, _ = _get_rbac_clients()
    if core_api is None:
        return []
    ns_list = core_api.list_namespace()
    return sorted(ns.metadata.name for ns in ns_list.items)


def _list_service_accounts_sync(namespace: str | None, include_system: bool) -> list[dict]:
    core_api, _ = _get_rbac_clients()
    if core_api is None:
        return []
    if namespace:
        sa_list = core_api.list_namespaced_service_account(namespace)
    else:
        sa_list = core_api.list_service_account_for_all_namespaces()
    items = [_serialize_service_account(sa) for sa in sa_list.items]
    if not include_system:
        items = [i for i in items if not i["is_system"]]
    return items


def _create_service_account_sync(name: str, namespace: str) -> dict:
    from kubernetes import client
    core_api, _ = _get_rbac_clients()
    if core_api is None:
        raise RuntimeError(_NO_CLUSTER)
    sa = client.V1ServiceAccount(metadata=client.V1ObjectMeta(name=name, namespace=namespace))
    created = core_api.create_namespaced_service_account(namespace, sa)
    return _serialize_service_account(created)


def _delete_service_account_sync(name: str, namespace: str) -> str:
    core_api, _ = _get_rbac_clients()
    if core_api is None:
        raise RuntimeError(_NO_CLUSTER)
    core_api.delete_namespaced_service_account(name, namespace)
    return f"ServiceAccount '{name}' deleted from namespace '{namespace}'"


def _list_roles_sync(namespace: str | None, include_system: bool) -> list[dict]:
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        return []
    if namespace:
        role_list = rbac_api.list_namespaced_role(namespace)
    else:
        role_list = rbac_api.list_role_for_all_namespaces()
    items = [_serialize_role(r) for r in role_list.items]
    if not include_system:
        items = [i for i in items if _should_include(i["name"], include_system)]
    return items


def _get_role_sync(name: str, namespace: str) -> dict:
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        raise RuntimeError(_NO_CLUSTER)
    role = rbac_api.read_namespaced_role(name, namespace)
    return _serialize_role(role)


def _create_role_sync(name: str, namespace: str, rules: list[dict]) -> dict:
    from kubernetes import client
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        raise RuntimeError(_NO_CLUSTER)
    role = client.V1Role(
        metadata=client.V1ObjectMeta(name=name, namespace=namespace),
        rules=[
            client.V1PolicyRule(
                api_groups=r.get("apiGroups", [""]),
                resources=r.get("resources", []),
                verbs=r.get("verbs", []),
            )
            for r in rules
        ],
    )
    created = rbac_api.create_namespaced_role(namespace, role)
    return _serialize_role(created)


def _delete_role_sync(name: str, namespace: str) -> str:
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        raise RuntimeError(_NO_CLUSTER)
    if _is_system(name):
        raise ValueError(f"Cannot delete system role '{name}'")
    rbac_api.delete_namespaced_role(name, namespace)
    return f"Role '{name}' deleted from namespace '{namespace}'"


def _list_cluster_roles_sync(include_system: bool) -> list[dict]:
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        return []
    cr_list = rbac_api.list_cluster_role()
    items = [_serialize_role(r) for r in cr_list.items]
    if not include_system:
        items = [i for i in items if _should_include(i["name"], include_system)]
    return items


def _get_cluster_role_sync(name: str) -> dict:
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        raise RuntimeError(_NO_CLUSTER)
    role = rbac_api.read_cluster_role(name)
    return _serialize_role(role)


def _create_cluster_role_sync(name: str, rules: list[dict]) -> dict:
    from kubernetes import client
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        raise RuntimeError(_NO_CLUSTER)
    cr = client.V1ClusterRole(
        metadata=client.V1ObjectMeta(name=name),
        rules=[
            client.V1PolicyRule(
                api_groups=r.get("apiGroups", [""]),
                resources=r.get("resources", []),
                verbs=r.get("verbs", []),
            )
            for r in rules
        ],
    )
    created = rbac_api.create_cluster_role(cr)
    return _serialize_role(created)


def _delete_cluster_role_sync(name: str) -> str:
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        raise RuntimeError(_NO_CLUSTER)
    if _is_system(name):
        raise ValueError(f"Cannot delete system ClusterRole '{name}'")
    rbac_api.delete_cluster_role(name)
    return f"ClusterRole '{name}' deleted"


def _list_role_bindings_sync(namespace: str | None, include_system: bool) -> list[dict]:
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        return []
    if namespace:
        rb_list = rbac_api.list_namespaced_role_binding(namespace)
    else:
        rb_list = rbac_api.list_role_binding_for_all_namespaces()
    items = [_serialize_binding(b) for b in rb_list.items]
    if not include_system:
        items = [i for i in items if _should_include(i["name"], include_system)]
    return items


def _create_role_binding_sync(name: str, namespace: str, role_ref: dict, subjects: list[dict]) -> dict:
    from kubernetes import client
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        raise RuntimeError(_NO_CLUSTER)
    rb = client.V1RoleBinding(
        metadata=client.V1ObjectMeta(name=name, namespace=namespace),
        role_ref=client.V1RoleRef(
            api_group="rbac.authorization.k8s.io",
            kind=role_ref.get("kind", "Role"),
            name=role_ref["name"],
        ),
        subjects=[
            client.V1Subject(
                kind=s.get("kind", "ServiceAccount"),
                name=s["name"],
                namespace=s.get("namespace", namespace),
            )
            for s in subjects
        ],
    )
    created = rbac_api.create_namespaced_role_binding(namespace, rb)
    return _serialize_binding(created)


def _delete_role_binding_sync(name: str, namespace: str) -> str:
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        raise RuntimeError(_NO_CLUSTER)
    if _is_system(name):
        raise ValueError(f"Cannot delete system RoleBinding '{name}'")
    rbac_api.delete_namespaced_role_binding(name, namespace)
    return f"RoleBinding '{name}' deleted from namespace '{namespace}'"


def _list_cluster_role_bindings_sync(include_system: bool) -> list[dict]:
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        return []
    crb_list = rbac_api.list_cluster_role_binding()
    items = [_serialize_binding(b) for b in crb_list.items]
    if not include_system:
        items = [i for i in items if _should_include(i["name"], include_system)]
    return items


def _create_cluster_role_binding_sync(name: str, role_ref: dict, subjects: list[dict]) -> dict:
    from kubernetes import client
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        raise RuntimeError(_NO_CLUSTER)
    crb = client.V1ClusterRoleBinding(
        metadata=client.V1ObjectMeta(name=name),
        role_ref=client.V1RoleRef(
            api_group="rbac.authorization.k8s.io",
            kind=role_ref.get("kind", "ClusterRole"),
            name=role_ref["name"],
        ),
        subjects=[
            client.V1Subject(
                kind=s.get("kind", "ServiceAccount"),
                name=s["name"],
                namespace=s.get("namespace"),
            )
            for s in subjects
        ],
    )
    created = rbac_api.create_cluster_role_binding(crb)
    return _serialize_binding(created)


def _delete_cluster_role_binding_sync(name: str) -> str:
    _, rbac_api = _get_rbac_clients()
    if rbac_api is None:
        raise RuntimeError(_NO_CLUSTER)
    if _is_system(name):
        raise ValueError(f"Cannot delete system ClusterRoleBinding '{name}'")
    rbac_api.delete_cluster_role_binding(name)
    return f"ClusterRoleBinding '{name}' deleted"


def _wizard_create_sync(name: str, namespace: str, scope: str, rules: list[dict]) -> dict:
    """Composite: create SA + Role/ClusterRole + Binding in one shot."""
    sa = _create_service_account_sync(name, namespace)
    role_name = f"{name}-role"
    binding_name = f"{name}-binding"

    if scope == "cluster":
        role = _create_cluster_role_sync(role_name, rules)
        binding = _create_cluster_role_binding_sync(
            binding_name,
            {"kind": "ClusterRole", "name": role_name},
            [{"kind": "ServiceAccount", "name": name, "namespace": namespace}],
        )
    else:
        role = _create_role_sync(role_name, namespace, rules)
        binding = _create_role_binding_sync(
            binding_name,
            namespace,
            {"kind": "Role", "name": role_name},
            [{"kind": "ServiceAccount", "name": name, "namespace": namespace}],
        )

    return {
        "service_account": sa,
        "role": role,
        "binding": binding,
    }


# ---------------------------------------------------------------------------
# WebSocket handlers
# ---------------------------------------------------------------------------

async def _rbac_namespaces(params: dict, ws: WebSocket, req_id: str):
    try:
        namespaces = await asyncio.to_thread(_list_namespaces_sync)
        await _ws._respond(ws, req_id, namespaces)
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_serviceaccounts_list(params: dict, ws: WebSocket, req_id: str):
    try:
        ns = params.get("namespace") or None
        include_system = params.get("include_system", False)
        items = await asyncio.to_thread(_list_service_accounts_sync, ns, include_system)
        await _ws._respond(ws, req_id, items)
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_serviceaccounts_create(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        namespace = params.get("namespace", "").strip()
        if not name:
            return await _ws._respond(ws, req_id, error="ServiceAccount name is required")
        if not namespace:
            return await _ws._respond(ws, req_id, error="Namespace is required")
        result = await asyncio.to_thread(_create_service_account_sync, name, namespace)
        db = _ws._db()
        try:
            await _ws.log_action(db, "created_service_account", "RBAC Management",
                                 json.dumps({"name": name, "namespace": namespace}),
                                 "service_account", f"{namespace}/{name}")
        finally:
            db.close()
        await _ws._respond(ws, req_id, result)
        await _ws._broadcast("rbac_updated", {"action": "created_service_account", "name": name, "namespace": namespace})
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_serviceaccounts_delete(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        namespace = params.get("namespace", "").strip()
        if not name or not namespace:
            return await _ws._respond(ws, req_id, error="Name and namespace are required")
        message = await asyncio.to_thread(_delete_service_account_sync, name, namespace)
        db = _ws._db()
        try:
            await _ws.log_action(db, "deleted_service_account", "RBAC Management",
                                 json.dumps({"name": name, "namespace": namespace}),
                                 "service_account", f"{namespace}/{name}")
        finally:
            db.close()
        await _ws._respond(ws, req_id, {"message": message})
        await _ws._broadcast("rbac_updated", {"action": "deleted_service_account", "name": name, "namespace": namespace})
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_roles_list(params: dict, ws: WebSocket, req_id: str):
    try:
        ns = params.get("namespace") or None
        include_system = params.get("include_system", False)
        items = await asyncio.to_thread(_list_roles_sync, ns, include_system)
        await _ws._respond(ws, req_id, items)
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_roles_get(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        namespace = params.get("namespace", "").strip()
        if not name or not namespace:
            return await _ws._respond(ws, req_id, error="Name and namespace are required")
        result = await asyncio.to_thread(_get_role_sync, name, namespace)
        await _ws._respond(ws, req_id, result)
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_roles_create(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        namespace = params.get("namespace", "").strip()
        rules = params.get("rules", [])
        if not name:
            return await _ws._respond(ws, req_id, error="Role name is required")
        if not namespace:
            return await _ws._respond(ws, req_id, error="Namespace is required")
        if not rules:
            return await _ws._respond(ws, req_id, error="At least one rule is required")
        result = await asyncio.to_thread(_create_role_sync, name, namespace, rules)
        db = _ws._db()
        try:
            await _ws.log_action(db, "created_role", "RBAC Management",
                                 json.dumps({"name": name, "namespace": namespace}),
                                 "role", f"{namespace}/{name}")
        finally:
            db.close()
        await _ws._respond(ws, req_id, result)
        await _ws._broadcast("rbac_updated", {"action": "created_role", "name": name, "namespace": namespace})
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_roles_delete(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        namespace = params.get("namespace", "").strip()
        if not name or not namespace:
            return await _ws._respond(ws, req_id, error="Name and namespace are required")
        message = await asyncio.to_thread(_delete_role_sync, name, namespace)
        db = _ws._db()
        try:
            await _ws.log_action(db, "deleted_role", "RBAC Management",
                                 json.dumps({"name": name, "namespace": namespace}),
                                 "role", f"{namespace}/{name}")
        finally:
            db.close()
        await _ws._respond(ws, req_id, {"message": message})
        await _ws._broadcast("rbac_updated", {"action": "deleted_role", "name": name, "namespace": namespace})
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_clusterroles_list(params: dict, ws: WebSocket, req_id: str):
    try:
        include_system = params.get("include_system", False)
        items = await asyncio.to_thread(_list_cluster_roles_sync, include_system)
        await _ws._respond(ws, req_id, items)
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_clusterroles_get(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        if not name:
            return await _ws._respond(ws, req_id, error="ClusterRole name is required")
        result = await asyncio.to_thread(_get_cluster_role_sync, name)
        await _ws._respond(ws, req_id, result)
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_clusterroles_create(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        rules = params.get("rules", [])
        if not name:
            return await _ws._respond(ws, req_id, error="ClusterRole name is required")
        if not rules:
            return await _ws._respond(ws, req_id, error="At least one rule is required")
        result = await asyncio.to_thread(_create_cluster_role_sync, name, rules)
        db = _ws._db()
        try:
            await _ws.log_action(db, "created_cluster_role", "RBAC Management",
                                 json.dumps({"name": name}),
                                 "cluster_role", name)
        finally:
            db.close()
        await _ws._respond(ws, req_id, result)
        await _ws._broadcast("rbac_updated", {"action": "created_cluster_role", "name": name})
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_clusterroles_delete(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        if not name:
            return await _ws._respond(ws, req_id, error="ClusterRole name is required")
        message = await asyncio.to_thread(_delete_cluster_role_sync, name)
        db = _ws._db()
        try:
            await _ws.log_action(db, "deleted_cluster_role", "RBAC Management",
                                 json.dumps({"name": name}),
                                 "cluster_role", name)
        finally:
            db.close()
        await _ws._respond(ws, req_id, {"message": message})
        await _ws._broadcast("rbac_updated", {"action": "deleted_cluster_role", "name": name})
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_rolebindings_list(params: dict, ws: WebSocket, req_id: str):
    try:
        ns = params.get("namespace") or None
        include_system = params.get("include_system", False)
        items = await asyncio.to_thread(_list_role_bindings_sync, ns, include_system)
        await _ws._respond(ws, req_id, items)
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_rolebindings_create(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        namespace = params.get("namespace", "").strip()
        role_ref = params.get("role_ref")
        subjects = params.get("subjects", [])
        if not name:
            return await _ws._respond(ws, req_id, error="RoleBinding name is required")
        if not namespace:
            return await _ws._respond(ws, req_id, error="Namespace is required")
        if not role_ref or not role_ref.get("name"):
            return await _ws._respond(ws, req_id, error="Role reference is required")
        if not subjects:
            return await _ws._respond(ws, req_id, error="At least one subject is required")
        result = await asyncio.to_thread(_create_role_binding_sync, name, namespace, role_ref, subjects)
        db = _ws._db()
        try:
            await _ws.log_action(db, "created_role_binding", "RBAC Management",
                                 json.dumps({"name": name, "namespace": namespace, "role": role_ref.get("name")}),
                                 "role_binding", f"{namespace}/{name}")
        finally:
            db.close()
        await _ws._respond(ws, req_id, result)
        await _ws._broadcast("rbac_updated", {"action": "created_role_binding", "name": name, "namespace": namespace})
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_rolebindings_delete(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        namespace = params.get("namespace", "").strip()
        if not name or not namespace:
            return await _ws._respond(ws, req_id, error="Name and namespace are required")
        message = await asyncio.to_thread(_delete_role_binding_sync, name, namespace)
        db = _ws._db()
        try:
            await _ws.log_action(db, "deleted_role_binding", "RBAC Management",
                                 json.dumps({"name": name, "namespace": namespace}),
                                 "role_binding", f"{namespace}/{name}")
        finally:
            db.close()
        await _ws._respond(ws, req_id, {"message": message})
        await _ws._broadcast("rbac_updated", {"action": "deleted_role_binding", "name": name, "namespace": namespace})
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_clusterrolebindings_list(params: dict, ws: WebSocket, req_id: str):
    try:
        include_system = params.get("include_system", False)
        items = await asyncio.to_thread(_list_cluster_role_bindings_sync, include_system)
        await _ws._respond(ws, req_id, items)
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_clusterrolebindings_create(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        role_ref = params.get("role_ref")
        subjects = params.get("subjects", [])
        if not name:
            return await _ws._respond(ws, req_id, error="ClusterRoleBinding name is required")
        if not role_ref or not role_ref.get("name"):
            return await _ws._respond(ws, req_id, error="Role reference is required")
        if not subjects:
            return await _ws._respond(ws, req_id, error="At least one subject is required")
        result = await asyncio.to_thread(_create_cluster_role_binding_sync, name, role_ref, subjects)
        db = _ws._db()
        try:
            await _ws.log_action(db, "created_cluster_role_binding", "RBAC Management",
                                 json.dumps({"name": name, "role": role_ref.get("name")}),
                                 "cluster_role_binding", name)
        finally:
            db.close()
        await _ws._respond(ws, req_id, result)
        await _ws._broadcast("rbac_updated", {"action": "created_cluster_role_binding", "name": name})
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_clusterrolebindings_delete(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        if not name:
            return await _ws._respond(ws, req_id, error="ClusterRoleBinding name is required")
        message = await asyncio.to_thread(_delete_cluster_role_binding_sync, name)
        db = _ws._db()
        try:
            await _ws.log_action(db, "deleted_cluster_role_binding", "RBAC Management",
                                 json.dumps({"name": name}),
                                 "cluster_role_binding", name)
        finally:
            db.close()
        await _ws._respond(ws, req_id, {"message": message})
        await _ws._broadcast("rbac_updated", {"action": "deleted_cluster_role_binding", "name": name})
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


async def _rbac_presets_list(params: dict, ws: WebSocket, req_id: str):
    await _ws._respond(ws, req_id, list(ROLE_PRESETS.values()))


async def _rbac_wizard_create(params: dict, ws: WebSocket, req_id: str):
    try:
        name = params.get("name", "").strip()
        namespace = params.get("namespace", "").strip()
        scope = params.get("scope", "namespace")
        preset_id = params.get("preset_id")
        custom_rules = params.get("custom_rules")
        existing_role = params.get("existing_role")

        if not name:
            return await _ws._respond(ws, req_id, error="Name is required")
        if not namespace:
            return await _ws._respond(ws, req_id, error="Namespace is required")

        # Determine rules
        if existing_role:
            # Bind to an existing role — only create SA + binding
            sa = await asyncio.to_thread(_create_service_account_sync, name, namespace)
            binding_name = f"{name}-binding"
            role_kind = existing_role.get("kind", "Role")
            role_name = existing_role["name"]

            if scope == "cluster" or role_kind == "ClusterRole":
                binding = await asyncio.to_thread(
                    _create_cluster_role_binding_sync, binding_name,
                    {"kind": "ClusterRole", "name": role_name},
                    [{"kind": "ServiceAccount", "name": name, "namespace": namespace}],
                )
            else:
                binding = await asyncio.to_thread(
                    _create_role_binding_sync, binding_name, namespace,
                    {"kind": role_kind, "name": role_name},
                    [{"kind": "ServiceAccount", "name": name, "namespace": namespace}],
                )

            result = {"service_account": sa, "role": None, "binding": binding, "used_existing_role": role_name}
        else:
            # Create new role from preset or custom rules
            if preset_id:
                preset = ROLE_PRESETS.get(preset_id)
                if not preset:
                    return await _ws._respond(ws, req_id, error=f"Unknown preset: {preset_id}")
                rules = preset["rules"]
                if preset["scope"] == "cluster":
                    scope = "cluster"
            elif custom_rules:
                rules = custom_rules
            else:
                return await _ws._respond(ws, req_id, error="Either preset_id, existing_role, or custom_rules is required")

            result = await asyncio.to_thread(_wizard_create_sync, name, namespace, scope, rules)

        db = _ws._db()
        try:
            await _ws.log_action(db, "created_rbac_user", "RBAC Management",
                                 json.dumps({
                                     "service_account": name,
                                     "namespace": namespace,
                                     "scope": scope,
                                     "preset": preset_id or "custom",
                                 }),
                                 "service_account", f"{namespace}/{name}")
        finally:
            db.close()

        await _ws._respond(ws, req_id, result)
        await _ws._broadcast("rbac_updated", {"action": "wizard_create", "name": name, "namespace": namespace})
    except Exception as e:
        await _ws._respond(ws, req_id, error=str(e))


# ---------------------------------------------------------------------------
# Action map
# ---------------------------------------------------------------------------

RBAC_ACTIONS = {
    "rbac.namespaces":                 _rbac_namespaces,
    "rbac.serviceaccounts.list":       _rbac_serviceaccounts_list,
    "rbac.serviceaccounts.create":     _rbac_serviceaccounts_create,
    "rbac.serviceaccounts.delete":     _rbac_serviceaccounts_delete,
    "rbac.roles.list":                 _rbac_roles_list,
    "rbac.roles.get":                  _rbac_roles_get,
    "rbac.roles.create":               _rbac_roles_create,
    "rbac.roles.delete":               _rbac_roles_delete,
    "rbac.clusterroles.list":          _rbac_clusterroles_list,
    "rbac.clusterroles.get":           _rbac_clusterroles_get,
    "rbac.clusterroles.create":        _rbac_clusterroles_create,
    "rbac.clusterroles.delete":        _rbac_clusterroles_delete,
    "rbac.rolebindings.list":          _rbac_rolebindings_list,
    "rbac.rolebindings.create":        _rbac_rolebindings_create,
    "rbac.rolebindings.delete":        _rbac_rolebindings_delete,
    "rbac.clusterrolebindings.list":   _rbac_clusterrolebindings_list,
    "rbac.clusterrolebindings.create": _rbac_clusterrolebindings_create,
    "rbac.clusterrolebindings.delete": _rbac_clusterrolebindings_delete,
    "rbac.presets.list":               _rbac_presets_list,
    "rbac.wizard.create":              _rbac_wizard_create,
}
