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

    # Default je produkcia: zabudnutá premenná nesmie zapnúť /api/docs ani
    # vývojárske logovanie. Lokálne si ENV=development nastav v .env.
    env: str = "production"

    # SQLAlchemy echo loguje každý SQL príkaz aj s parametrami, teda osobné
    # údaje uchádzačov a hashe hesiel pri zápise. Zapína sa len explicitne,
    # nezávisle od ENV, a v produkcii nikdy.
    sql_echo: bool = False

    # Rate limiting za reverznou proxy (nginx, Cloud Run).
    # Zapni LEN ak pred appkou skutočne stojí proxy, ktorej veríš. Inak by si
    # hocikomu dovolil obísť limit podvrhnutou hlavičkou X-Forwarded-For.
    # TRUSTED_PROXY_HOPS = počet vlastných proxy medzi klientom a appkou:
    #   nginx na tom istom hostovi alebo priamy Cloud Run URL -> 0
    #   Cloud Run za externým HTTP(S) load balancerom           -> 1
    trust_proxy_headers: bool = False
    trusted_proxy_hops: int = 0

    # AI (Gemini). Bez kľúča alebo s AI_ENABLED=false beží chatbot ako stub
    # a hodnotenie uchádzačov sa preskočí (uchádzač ostane bez skóre).
    ai_enabled: bool = True
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-3.1-flash-lite"
    gemini_extraction_model: str = "gemini-3.1-flash-lite"

    # Posledná poistka v kóde proti vyčerpaniu kreditu: strop na počet volaní
    # modelu za deň. 0 = bez stropu. Platí na instanciu procesu, takže to
    # NENAHRADZUJE kvótu a billing budget v Google Cloud — je to len záchranná
    # brzda pre prípad chyby v kóde alebo útoku, ktorý prejde rate limitom.
    ai_daily_call_limit: int = 0

    @property
    def ai_available(self) -> bool:
        return self.ai_enabled and bool(self.gemini_api_key)


settings = Settings()
