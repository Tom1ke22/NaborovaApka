from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480

    storage_backend: str = "local"  # "local" | "gcs"
    gcs_bucket_name: str = ""
    google_application_credentials: str = ""

    # Čiarkami oddelený zoznam CORS origins
    # Lokálne: "http://localhost:5173,http://localhost:3000"
    # GCP:     "https://naborovaapka.sk"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    env: str = "development"

    # AI (Gemini). Bez kľúča alebo s AI_ENABLED=false beží chatbot ako stub
    # a hodnotenie uchádzačov sa preskočí (uchádzač ostane bez skóre).
    ai_enabled: bool = True
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-3.1-flash-lite"
    gemini_extraction_model: str = "gemini-3.1-flash-lite"

    @property
    def ai_available(self) -> bool:
        return self.ai_enabled and bool(self.gemini_api_key)


settings = Settings()
