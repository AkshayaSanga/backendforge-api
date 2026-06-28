from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.redis import close_redis, get_redis
from app.middleware.exception_handler import global_exception_handler, value_error_handler
from app.middleware.logging import RequestLoggingMiddleware
from app.utils.seed import seed_admin
from app.db.session import AsyncSessionLocal

from app.api.routes import auth, users, files, admin, health

setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup.begin", env=settings.APP_ENV)

    # Initialise Redis connection
    await get_redis()

    # Seed admin user on first run
    async with AsyncSessionLocal() as db:
        await seed_admin(db)

    logger.info("startup.complete")
    yield

    logger.info("shutdown.begin")
    await close_redis()
    logger.info("shutdown.complete")


app = FastAPI(
    title="BackendForge API",
    description=(
        "Production-ready FastAPI backend with auth, RBAC, Redis caching, "
        "background jobs, file uploads and more."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)

# ── Routers ───────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
