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
