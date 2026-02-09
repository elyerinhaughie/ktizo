"""Helm CLI wrapper with async subprocess execution."""
import asyncio
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class HelmRunner:
    def __init__(self):
        self.helm_bin = self._find_helm()
        self.kubeconfig = str(Path.home() / ".kube" / "config")

    def _find_helm(self) -> str:
        # Check project directory first
        project_helm = Path(__file__).resolve().parent.parent.parent / "helm"
        if project_helm.is_file():
            return str(project_helm)
        # Fallback to PATH
        which = shutil.which("helm")
        if which:
            return which
        logger.warning("helm binary not found")
        return "helm"

    async def _run_helm(self, args: list, timeout: int = 300) -> Tuple[int, str, str]:
        env = os.environ.copy()
        env["KUBECONFIG"] = self.kubeconfig
        logger.info(f"Running: helm {' '.join(args)}")
        proc = await asyncio.create_subprocess_exec(
            self.helm_bin, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return -1, "", "Helm command timed out"
        return proc.returncode, stdout.decode(), stderr.decode()

    async def repo_add(self, name: str, url: str) -> Tuple[bool, str]:
        rc, out, err = await self._run_helm(["repo", "add", name, url, "--force-update"])
        if rc != 0:
            return False, err.strip() or out.strip()
        return True, out.strip()

    async def repo_update(self) -> Tuple[bool, str]:
        rc, out, err = await self._run_helm(["repo", "update"])
        if rc != 0:
            return False, err.strip() or out.strip()
        return True, out.strip()

    async def install(
        self,
        release_name: str,
        chart: str,
        namespace: str,
        version: str = None,
        values_yaml: str = None,
    ) -> Tuple[bool, str]:
        args = ["install", release_name, chart, "--namespace", namespace, "--create-namespace", "--wait", "--timeout", "10m"]
        if version:
            args.extend(["--version", version])

        tmp_file = None
        try:
            if values_yaml:
                tmp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
                tmp_file.write(values_yaml)
                tmp_file.close()
                args.extend(["-f", tmp_file.name])

            rc, out, err = await self._run_helm(args, timeout=660)
            combined = (out.strip() + "\n" + err.strip()).strip()
            if rc != 0:
                return False, combined or "Unknown error"
            return True, combined
        finally:
            if tmp_file:
                try:
                    os.unlink(tmp_file.name)
                except OSError:
                    pass

    async def upgrade(
        self,
        release_name: str,
        chart: str,
        namespace: str,
        version: str = None,
        values_yaml: str = None,
    ) -> Tuple[bool, str]:
        args = ["upgrade", release_name, chart, "--namespace", namespace, "--wait", "--timeout", "10m"]
        if version:
            args.extend(["--version", version])

        tmp_file = None
        try:
            if values_yaml:
                tmp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
                tmp_file.write(values_yaml)
                tmp_file.close()
                args.extend(["-f", tmp_file.name])

            rc, out, err = await self._run_helm(args, timeout=660)
            combined = (out.strip() + "\n" + err.strip()).strip()
            if rc != 0:
                return False, combined or "Unknown error"
            return True, combined
        finally:
            if tmp_file:
                try:
                    os.unlink(tmp_file.name)
                except OSError:
                    pass

    async def uninstall(self, release_name: str, namespace: str) -> Tuple[bool, str]:
        rc, out, err = await self._run_helm(["uninstall", release_name, "--namespace", namespace, "--wait"])
        combined = (out.strip() + "\n" + err.strip()).strip()
        if rc != 0:
            return False, combined or "Unknown error"
        return True, combined

    async def get_status(self, release_name: str, namespace: str) -> Optional[dict]:
        rc, out, err = await self._run_helm(["status", release_name, "--namespace", namespace, "-o", "json"])
        if rc != 0:
            return None
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return None

    async def list_releases(self) -> list:
        rc, out, err = await self._run_helm(["list", "--all-namespaces", "-o", "json"])
        if rc != 0:
            return []
        try:
            return json.loads(out) or []
        except json.JSONDecodeError:
            return []

    async def search_versions(self, chart: str) -> list:
        rc, out, err = await self._run_helm(["search", "repo", chart, "--versions", "-o", "json"])
        if rc != 0:
            return []
        try:
            return json.loads(out) or []
        except json.JSONDecodeError:
            return []


# Singleton
helm_runner = HelmRunner()


def wizard_to_values(flat: dict) -> dict:
    """Convert dot-notation keys to nested dict.

    {"grafana.adminPassword": "secret"} → {"grafana": {"adminPassword": "secret"}}
    """
    result = {}
    for key, value in flat.items():
        parts = key.split(".")
        d = result
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        d[parts[-1]] = value
    return result
