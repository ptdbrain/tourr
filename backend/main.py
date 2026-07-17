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
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

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
    # Startup
    logger.info(f"🛡️ {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    logger.info(f"   Languages: {', '.join(settings.SUPPORTED_LANGUAGES)}")
    logger.info(f"   Gemini API: {'✅ configured' if settings.gemini_key else '❌ missing'}")

    # Initialize price database
    from app.data.price_db import init_price_db
    init_price_db()
    logger.info("   Price DB: ✅ initialized")

    yield

    # Shutdown
    logger.info(f"🛡️ {settings.APP_NAME} shutting down...")


# ── App ──────────────────────────────────────────────────
app = FastAPI(
    title="Tour-resQ API",
    description="AI-powered tourist protection assistant for Vietnam",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Hackathon mode — open CORS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount frontend static files ──────────────────────────
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")


# ── Register API routes ──────────────────────────────────
from app.api.routes import router as api_router
app.include_router(api_router, prefix="/api")


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
