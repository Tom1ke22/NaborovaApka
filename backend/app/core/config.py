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


settings = Settings()
