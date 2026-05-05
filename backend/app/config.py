from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    openai_api_key: str
    supabase_anon_key: str = ""  # usado só no frontend — Railway não precisa definir
    # CORS origins (comma-separated)
    cors_origins: str = "http://localhost:5173,https://corrigeai.vercel.app"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
