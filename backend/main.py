import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import structlog

from app.config import settings
from app.database import engine, Base
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import auth, products, contacts, campaigns, leads, content, approvals, agent
from app.routers import rates, listings, dpa
from app.routers import outreach, tracking
from app.routers import unsubscribe
from app.routers import flyers

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("MortgageSesame API starting", env=settings.app_env)
    # Auto-create tables in development (use alembic for production)
    if settings.app_env == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Auto-create internal admin seed account if configured
    if settings.admin_seed_email and settings.admin_seed_password:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.middleware.auth import hash_password
        from app.models.user import User, UserRole
        async with AsyncSession(engine, expire_on_commit=False) as db:
            result = await db.execute(select(User).where(User.email == settings.admin_seed_email))
            if result.scalar_one_or_none() is None:
                admin = User(
                    email=settings.admin_seed_email,
                    hashed_password=hash_password(settings.admin_seed_password),
                    full_name=settings.admin_seed_full_name or settings.admin_seed_email.split("@")[0],
                    nmls_id=settings.admin_seed_nmls_id or None,
                    role=UserRole.ADMIN,
                    is_active=True,
                    is_verified=True,
                )
                db.add(admin)
                await db.commit()
                log.info("admin_seed.created", email=settings.admin_seed_email)
            else:
                log.info("admin_seed.exists", email=settings.admin_seed_email)

    yield
    log.info("MortgageSesame API shutting down")
    await engine.dispose()


app = FastAPI(
    title="MortgageSesame API",
    description="AI-powered mortgage acquisition operating system",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(contacts.router, prefix="/api/v1")
app.include_router(campaigns.router, prefix="/api/v1")
app.include_router(leads.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")
app.include_router(rates.router, prefix="/api/v1")
app.include_router(listings.router, prefix="/api/v1")
app.include_router(dpa.router, prefix="/api/v1")
app.include_router(outreach.router, prefix="/api/v1")
app.include_router(tracking.router, prefix="/api/v1")
app.include_router(tracking.short_router)           # /r/{code} at root for short QR URLs
app.include_router(flyers.router, prefix="/api/v1")
app.include_router(unsubscribe.router)              # /unsubscribe at root (CAN-SPAM)


# Serve all generated media (audio, avatars, flyers, thumbnails)
_media_dir = os.getenv("MEDIA_STORAGE_PATH", "./media")
for _sub in ["", "avatar", "avatars", "flyers", "listings"]:
    os.makedirs(os.path.join(_media_dir, _sub) if _sub else _media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=_media_dir), name="media")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
