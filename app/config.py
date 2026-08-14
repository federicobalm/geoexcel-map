from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GeoExcel Map v3"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    max_upload_mb: int = 15
    session_ttl_hours: int = 12

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def session_dir(self) -> Path:
        return self.data_dir / "sessions"

    @property
    def export_dir(self) -> Path:
        return self.data_dir / "exports"


settings = Settings()
