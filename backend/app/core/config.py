from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ktizo"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Templates
    TEMPLATES_DIR: str = "../templates"

    # Compiled configurations output directory
    COMPILED_DIR: str = "../compiled"

    # TFTP/PXE Settings
    TFTP_ROOT: str = "/var/lib/tftpboot"

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
