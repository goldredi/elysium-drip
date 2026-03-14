from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://emojirean:emojirean_secret@localhost:5432/emojirean"
    redis_url: str = "redis://:redis_secret@localhost:6379/0"
    bot_token: str = ""
    webapp_url: str = "http://localhost:8000"
    access_codes: str = "lain,drip,wired,cipher,ghost,nyan,driptech,layer07"
    admin_secret: str = "admin_secret_change_me"
    secret_key: str = "secret_key_change_me"
    token_expire_hours: int = 72

    @property
    def access_code_list(self) -> list[str]:
        return [c.strip().lower() for c in self.access_codes.split(",") if c.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
