from pydantic_settings import BaseSettings, SettingsConfigDict

# (input_tokens, output_tokens) por pacote de recarga
PACOTES_TOKENS: dict[str, tuple[int, int]] = {
    "starter": (5_000_000, 5_000_000),
    "regular": (8_000_000, 8_000_000),
    "pro": (12_000_000, 12_000_000),
}

PACOTES_PRECO_CENTAVOS: dict[str, int] = {
    "starter": 9900,   # R$ 99,00
    "regular": 15900,  # R$ 159,00
    "pro": 23900,      # R$ 239,00
}


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    openai_api_key: str
    # CORS origins (comma-separated)
    cors_origins: str = "http://localhost:5173"
    # AbacatePay
    abacatepay_api_key: str = ""
    abacatepay_webhook_secret: str = ""
    abacatepay_produto_starter_id: str = "prod_SR6mEYqRaGb2ZRZhuPQukPWj"
    abacatepay_produto_regular_id: str = "prod_unqPxjFG5ytKf3PpcdJugjsd"
    abacatepay_produto_pro_id: str = "prod_tL6xTH3jDNS6KucjWEsCW2uu"
    frontend_url: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    def produto_id(self, pacote: str) -> str:
        return {
            "starter": self.abacatepay_produto_starter_id,
            "regular": self.abacatepay_produto_regular_id,
            "pro": self.abacatepay_produto_pro_id,
        }[pacote]


settings = Settings()
