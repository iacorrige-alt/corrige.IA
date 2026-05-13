from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    openai_api_key: str
    # CORS origins (comma-separated)
    cors_origins: str = "http://localhost:5173"
    # AbacatePay
    abacatepay_api_key: str = ""
    abacatepay_webhook_secret: str = ""
    abacatepay_product_id: str = "prod_sCLyTm2XyfrrUT4CyNkjfJ1j"
    abacatepay_preco_centavos: int = 9900  # R$ 99,00
    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
