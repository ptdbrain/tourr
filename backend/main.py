"""
Tour-resQ — AI-Powered Tourist Protection Assistant
====================================================
Main FastAPI application.

Three core features:
1. Instant fair-price checks (photo → OCR → anomaly detection)
2. Scam pattern detection (voice/text → pattern matching + AI analysis)
3. Emergency SOS dispatch (GPS + photo + context → webhook)

All features are multilingual: EN, KO, ZH, RU
"""
from dotenv import load_dotenv
load_dotenv()

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.core.config import settings
from app.i18n.translations import get_supported_languages


# ── Lifespan ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"🛡️ {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    logger.info(f"   Languages: {', '.join(settings.SUPPORTED_LANGUAGES)}")
    logger.info(f"   Gemini API: {'✅ configured' if settings.gemini_key else '❌ missing'}")

    yield

    # Shutdown
    logger.info(f"🛡️ {settings.APP_NAME} shutting down...")

# Initialize price database (Global scope for Vercel Serverless compatibility)
try:
    from app.data.price_db import init_price_db
    init_price_db()
    logger.info("   Price DB: ✅ initialized")
except Exception as e:
    logger.error(f"Failed to init DB: {e}")


from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ── Rate Limiting Setup ──────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── App ──────────────────────────────────────────────────
app = FastAPI(
    title="Tour-resQ API",
    description="AI-powered tourist protection assistant for Vietnam",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restrict to necessary origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── Mount frontend static files ──────────────────────────
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")


# ── Register API routes ──────────────────────────────────
from app.api.routes import router as api_router
from app.api.live_negotiation import router as live_router

app.include_router(api_router)
app.include_router(live_router)


# ── Root endpoint ────────────────────────────────────────
@app.get("/")
async def root():
    """Root endpoint with app info and available languages."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "languages": get_supported_languages(),
        "features": [
            "price-check",
            "scam-detect",
            "translate",
            "sos-dispatch",
        ],
        "frontend": "/app/index.html",
    }


@app.get("/health")
async def health():
    """Health check for deployment monitoring."""
    return {"status": "ok", "version": settings.APP_VERSION}


# ── Run directly ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
