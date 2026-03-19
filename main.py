from fastapi import FastAPI
from app.api.errors import register_exception_handlers
from app.api.routes.lead import router as lead_router
from app.core.config import Settings
from app.services.cache import InMemoryCache
from app.services.cleaning_service import CleaningService


def create_app() -> FastAPI:
    settings = Settings()  # reads .env via pydantic-settings
    cache = InMemoryCache(ttl_seconds=settings.CACHE_TTL_SECONDS)
    cleaning_service = CleaningService(settings=settings, cache=cache)

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
    )

    app.state.settings = settings
    app.state.cleaning_service = cleaning_service

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": settings.APP_NAME, "docs": "/docs", "openapi": "/openapi.json"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    register_exception_handlers(app)
    app.include_router(lead_router)

    return app


app = create_app()

