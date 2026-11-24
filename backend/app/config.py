from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    storage_root: Path = Path("../vault")
    database_url: str = "sqlite:///../data/modelvault.db"
    allowed_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MODEL_VAULT_")

    @property
    def origins(self):
        return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]


settings = Settings()
settings.storage_root.mkdir(parents=True, exist_ok=True)
