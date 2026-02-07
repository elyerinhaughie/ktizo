from pydantic_settings import BaseSettings
from pathlib import Path
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ktizo"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Templates - stay in project directory (part of codebase)
    TEMPLATES_DIR: str = "../templates"

    # Compiled configurations output directory - default to ~/.ktizo/compiled
    COMPILED_DIR: str = str(Path.home() / ".ktizo" / "compiled")

    # Data directory - default to ~/.ktizo/data
    DATA_DIR: str = str(Path.home() / ".ktizo" / "data")

    # Logs directory - default to ~/.ktizo/logs
    LOGS_DIR: str = str(Path.home() / ".ktizo" / "logs")

    # TFTP/PXE Settings
    TFTP_ROOT: str = "/var/lib/tftpboot"

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()


def ensure_v_prefix(version: str) -> str:
    """Ensure a version string has 'v' prefix (e.g., '1.12.2' -> 'v1.12.2')"""
    if version and not version.startswith('v'):
        return f'v{version}'
    return version


def strip_v_prefix(version: str) -> str:
    """Strip 'v' prefix from a version string (e.g., 'v1.35.0' -> '1.35.0')"""
    if version and version.startswith('v'):
        return version[1:]
    return version
