from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "1Cat Hermes OS Runtime"
    environment: str = "development"
    database_url: str = "sqlite:///./onecat.db"
    auth_mode: str = "development"
    oidc_issuer: str = "http://localhost:8080/auth/realms/1cat"
    oidc_jwks_url: str = "http://keycloak:8080/auth/realms/1cat/protocol/openid-connect/certs"
    oidc_audience: str = "1cat-workspace"
    hermes_execution_enabled: bool = False
    hermes_pma_url: str = "http://hermes-pma:8080"
    hermes_bga_url: str = "http://hermes-bga:8080"
    hermes_mo_url: str = "http://hermes-mo:8080"
    hermes_api_key_pma: str = ""
    hermes_api_key_bga: str = ""
    hermes_api_key_mo: str = ""
    pii_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()

