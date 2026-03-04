from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "KOMODO_MCP_"}

    KOMODO_URL: str
    KOMODO_API_KEY: str
    KOMODO_API_SECRET: str
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Full OAuth 2.1 authorization server (KomodoOAuthProvider)
    # All three required to enable; BASE_URL must be the public URL of this server
    OAUTH_JWT_SECRET: str | None = None
    OAUTH_PASSWORD: str | None = None
    BASE_URL: str | None = None


settings = Settings()  # type: ignore[call-arg]
