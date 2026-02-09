"""Service for generating Talos Factory schematics."""
import httpx
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

FACTORY_API_URL = "https://factory.talos.dev/schematics"


def uri_to_short_name(image_uri: str) -> str:
    """Convert a full image URI to Factory API short name.

    'ghcr.io/siderolabs/iscsi-tools:v0.1.6' -> 'siderolabs/iscsi-tools'
    'ghcr.io/siderolabs/drbd:v9.2.12' -> 'siderolabs/drbd'
    'siderolabs/iscsi-tools' -> 'siderolabs/iscsi-tools' (already short)
    """
    # Strip tag
    without_tag = image_uri.split(":")[0]
    # Strip registry prefix (ghcr.io/)
    parts = without_tag.split("/")
    if len(parts) >= 3:
        return "/".join(parts[1:])
    elif len(parts) == 2:
        return "/".join(parts)
    return without_tag


def build_factory_installer_url(schematic_id: str, talos_version: str) -> str:
    """Build the factory installer URL from a schematic ID and version."""
    from app.core.config import ensure_v_prefix
    version = ensure_v_prefix(talos_version)
    return f"factory.talos.dev/installer/{schematic_id}:{version}"


async def generate_schematic(extension_uris: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """Call the Talos Factory API to generate a schematic.

    Args:
        extension_uris: List of image URIs or short names.

    Returns:
        Tuple of (schematic_id, error_message). On success error is None.
    """
    short_names = [uri_to_short_name(uri) for uri in extension_uris]

    payload = {
        "customization": {
            "systemExtensions": {
                "officialExtensions": short_names,
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(FACTORY_API_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            schematic_id = data.get("id")
            if not schematic_id:
                return None, "Factory API returned no schematic ID"
            logger.info(f"Generated factory schematic: {schematic_id} for extensions: {short_names}")
            return schematic_id, None
    except httpx.TimeoutException:
        msg = "Talos Factory API timed out"
        logger.error(msg)
        return None, msg
    except httpx.HTTPStatusError as e:
        msg = f"Talos Factory API error: {e.response.status_code} {e.response.text[:200]}"
        logger.error(msg)
        return None, msg
    except Exception as e:
        msg = f"Talos Factory API error: {e}"
        logger.error(msg)
        return None, msg


async def resolve_install_image(
    extension_uris: List[str], talos_version: str
) -> Tuple[str, Optional[str]]:
    """Resolve the correct install_image URL for given extensions and version.

    If no extensions, returns the vanilla factory installer.
    If extensions exist, calls Factory API and returns factory URL.

    Returns:
        Tuple of (install_image_url, error_message). Error is None on success.
    """
    from app.core.config import ensure_v_prefix
    version = ensure_v_prefix(talos_version)

    if not extension_uris:
        return f"factory.talos.dev/installer/{version}", None

    schematic_id, error = await generate_schematic(extension_uris)
    if error:
        return f"ghcr.io/siderolabs/installer:{version}", error

    return build_factory_installer_url(schematic_id, talos_version), None
