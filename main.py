import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from core.config import settings, ALLOWED_ORIGINS
from core.limiter import limiter
from core.logging_config import setup_logging, get_logger
from core.database import Base, engine
from models import db_models  # noqa: F401 — registers all ORM models with Base
from routers import health, chat, contact

setup_logging()
logger = get_logger(__name__)

# NOTE: Base.metadata.create_all is intentionally NOT called here.
# Schema is managed by Alembic (runs before uvicorn in the start command).
# Calling create_all at import time crashes uvicorn if the DB isn't ready yet.


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Safety net: create tables if alembic migration was skipped or failed.
    # create_all is a no-op if tables already exist.
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema verified.")
    except Exception as exc:
        logger.warning("DB schema check failed: %s", exc)

    # Run vector store init in a thread so uvicorn starts serving immediately.
    def _build_index() -> None:
        try:
            from services.rag_service import build_index
            build_index()
            logger.info("Vector store ready")
        except Exception as exc:
            logger.warning("Vector store init skipped: %s", exc)

    logger.info("Starting up — initializing vector store in background...")
    asyncio.get_event_loop().run_in_executor(None, _build_index)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="askSashkoAi",
    version=settings.app_version,
    description="AI-powered portfolio chatbot — talk to Sashko Milushev",
    lifespan=lifespan,
    # Hide docs in production
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
)

# ── Slowapi ────────────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)


# ── Security headers ───────────────────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.app_env != "development":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ── Global exception handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Validation error handler ───────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{"field": e["loc"][-1], "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health.router, tags=["health"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(contact.router, prefix="/contact", tags=["contact"])

# ── Static frontend ────────────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")

logger.info("askSashkoAi ready | env=%s | version=%s", settings.app_env, settings.app_version)
