"""Utility for Kubernetes API operations from backend services."""
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


def _get_k8s_client():
    """Load a CoreV1Api client from ~/.kube/config. Returns None on failure."""
    from kubernetes import client, config

    kubeconfig = Path.home() / ".kube" / "config"
    if not kubeconfig.exists():
        return None

    config.load_kube_config(config_file=str(kubeconfig))
    return client.CoreV1Api()


def kubectl_delete_node(hostname: str) -> Tuple[bool, str]:
    """Delete a Kubernetes node by name. Best-effort — never raises."""
    try:
        api = _get_k8s_client()
        if api is None:
            return False, "kubeconfig not found at ~/.kube/config"

        api.delete_node(name=hostname)
        msg = f"Deleted Kubernetes node '{hostname}'"
        logger.info(msg)
        return True, msg
    except Exception as e:
        # Catch everything: ApiException (404 = already gone), connection errors, etc.
        err = str(e)
        if "404" in err or "not found" in err.lower():
            msg = f"Node '{hostname}' not found in cluster (already removed)"
            logger.info(msg)
            return True, msg
        msg = f"Failed to delete node '{hostname}': {err}"
        logger.warning(msg)
        return False, msg
