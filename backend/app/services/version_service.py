"""Fetch available Talos and Kubernetes versions from GitHub releases."""

import logging
import re
import time
from typing import List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

CACHE_TTL = 900  # 15 minutes

_cache: dict[str, Tuple[float, List[str]]] = {}


def _semver_key(version: str) -> Tuple[int, ...]:
    """Parse '1.34.1' into (1, 34, 1) for sorting."""
    parts = re.split(r"[.\-]", version.lstrip("v"))
    return tuple(int(p) if p.isdigit() else 0 for p in parts)


async def _fetch_github_releases(repo: str, per_page: int = 50) -> list[dict]:
    url = f"https://api.github.com/repos/{repo}/releases"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params={"per_page": per_page})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"GitHub API error for {repo}: {e}")
        return []


async def fetch_talos_versions() -> List[str]:
    key = "talos"
    if key in _cache:
        ts, versions = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return versions

    releases = await _fetch_github_releases("siderolabs/talos", per_page=30)
    versions = []
    for r in releases:
        if r.get("draft") or r.get("prerelease"):
            continue
        tag = r.get("tag_name", "")
        if tag:
            versions.append(tag)

    if versions:
        _cache[key] = (time.time(), versions)
    return versions


async def fetch_kubernetes_versions() -> List[str]:
    key = "kubernetes"
    if key in _cache:
        ts, versions = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return versions

    releases = await _fetch_github_releases("kubernetes/kubernetes", per_page=50)
    versions = []
    for r in releases:
        if r.get("draft") or r.get("prerelease"):
            continue
        tag = r.get("tag_name", "")
        if not tag:
            continue
        # Skip alpha, beta, rc
        if re.search(r"(alpha|beta|rc)", tag, re.IGNORECASE):
            continue
        # Strip leading v
        version = tag.lstrip("v")
        versions.append(version)

    versions.sort(key=_semver_key, reverse=True)
    if versions:
        _cache[key] = (time.time(), versions)
    return versions
