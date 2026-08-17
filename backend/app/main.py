from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging_config import setup_logging

setup_logging(settings.env)

app = FastAPI(
    title="Recruitment App API",
    version="0.1.0",
    docs_url="/api/docs" if settings.env == "development" else None,
    redoc_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "env": settings.env}
