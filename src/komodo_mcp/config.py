from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "KOMODO_MCP_"}

    KOMODO_URL: str
    KOMODO_API_KEY: str
    KOMODO_API_SECRET: str
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    AUTH_TOKEN: str | None = None


settings = Settings()  # type: ignore[call-arg]
