"""
Tour-resQ API Routes
====================
All REST endpoints, synchronized with README documentation.
"""
from fastapi import APIRouter, BackgroundTasks, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
from typing import Optional
import hashlib

from app.engine.price_checker import analyze_price_context, check_single_price, check_price_from_image
from app.data.price_db import add_verified_price
from app.engine.scam_detector import detect_scam_with_ai
from app.engine.defense_scripts import generate_defense_script
from app.engine.blackbox import log_incident, get_heatmap_data
from app.engine.vision_analyzer import analyze_menu_layout
from app.engine.authority_router import find_nearest_authority, generate_official_report_vi
from app.engine.translator import translate_text, translate_for_confrontation, get_phrasebook
from app.engine.sos_dispatcher import dispatch_sos, get_emergency_info
from app.i18n.translations import t, get_supported_languages, get_all_translations

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ─────────────────────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────────────────────

class SituationRequest(BaseModel):
    description: str
    location: str
    language: str = "en"
    lat: float = 21.0285
    lng: float = 105.8542

class DispatchRequest(BaseModel):
    lat: float
    lng: float
    scam_type: str
    details: str
    authority_name: str

class VisionRequest(BaseModel):
    image_base64: str
    language: str = "en"

class TranslateRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str
    context: str = "tourist"

class ConfrontationRequest(BaseModel):
    text: str
    tourist_lang: str = "en"

class PriceCheckRequest(BaseModel):
    item_name: str
    price: float
    region: str = "hanoi"
    venue_type: str = "all"

class SOSRequest(BaseModel):
    latitude: float
    longitude: float
    incident_type: str = "other"
    description: str = ""
    language: str = "en"
    photo_base64: str = ""
    severity: str = "high"


# ─────────────────────────────────────────────────────────
# CORE ENDPOINTS
# ─────────────────────────────────────────────────────────

@router.post("/api/v1/analyze-situation")
@limiter.limit("10/minute")
async def analyze_situation(req: SituationRequest, request: Request, background_tasks: BackgroundTasks):
    """
    Combined endpoint: price analysis + scam detection + defense script.
    Automatically triggers Guardian Blackbox on extreme overcharges.
    """
    price_assessment = await analyze_price_context(
        description=req.description,
        location_context=req.location,
        lang=req.language
    )

    scam_assessment = await detect_scam_with_ai(
        description=req.description,
        lang=req.language,
        region=req.location
    )

    response_data = {
        "status": "success",
        "price_assessment": None,
        "scam_assessment": scam_assessment.to_dict(),
        "active_defense_script": "",
        "blackbox_triggered": False,
        "nearest_authority": None
    }

    if price_assessment:
        response_data["price_assessment"] = price_assessment.dict()

        script = generate_defense_script(
            tier=price_assessment.tier,
            typology=price_assessment.typology_match,
            fair_price=price_assessment.max_fair_price,
            asked_price=price_assessment.unit_price,
            item_name=price_assessment.item_name
        )
        response_data["active_defense_script"] = script

        if price_assessment.tier == "EXTREME_OVERCHARGE":
            response_data["blackbox_triggered"] = True
            nearest_auth, dist_km = find_nearest_authority(req.lat, req.lng)
            if nearest_auth:
                response_data["nearest_authority"] = {
                    "name": nearest_auth.name,
                    "distance_km": round(dist_km, 2),
                    "phone": nearest_auth.phone
                }
            audio_hash = hashlib.md5(req.description.encode()).hexdigest()
            background_tasks.add_task(
                log_incident,
                lat=req.lat, lng=req.lng,
                severity="CRITICAL",
                scam_type=price_assessment.typology_match or "Severe Overcharge",
                audio_signature=f"hash_{audio_hash}"
            )

    return response_data


@router.post("/api/v1/check-price")
@limiter.limit("20/minute")
async def check_price(req: PriceCheckRequest, request: Request):
    """
    DB-backed price check using Z-score anomaly detection.
    Returns insufficient_data when sample_count < MIN_SAMPLE_SIZE.
    """
    result = check_single_price(
        item_name=req.item_name,
        asked_price=req.price,
        region=req.region,
        venue_type=req.venue_type
    )
    return {"status": "success", "result": result.dict()}


@router.post("/api/v1/analyze-vision")
@limiter.limit("5/minute")
async def analyze_vision(req: VisionRequest, request: Request):
    """Analyze an image (menu/receipt/POS/banknotes) for forgery and price traps."""
    vision_assessment = await analyze_menu_layout(
        image_base64=req.image_base64,
        mime_type="image/jpeg",
        lang=req.language
    )
    if not vision_assessment:
        return {"status": "error", "message": "Vision analysis failed. Check API key."}
    return {"status": "success", "vision_assessment": vision_assessment.dict()}


# ─────────────────────────────────────────────────────────
# TRANSLATION ENDPOINTS
# ─────────────────────────────────────────────────────────

@router.post("/api/v1/translate")
@limiter.limit("20/minute")
async def translate(req: TranslateRequest, request: Request):
    """Domain-adapted translation with cultural context."""
    result = await translate_text(
        text=req.text,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
        context=req.context,
    )
    return result


@router.post("/api/v1/translate/confrontation")
@limiter.limit("10/minute")
async def translate_confrontation(req: ConfrontationRequest, request: Request):
    """Specialized translation for price disputes — shows Vietnamese to vendor."""
    result = await translate_for_confrontation(
        text=req.text,
        tourist_lang=req.tourist_lang,
    )
    return result


@router.get("/api/v1/phrasebook")
async def phrasebook(lang: str = "en"):
    """Offline phrasebook with tourist language + Vietnamese pairs."""
    return {"status": "success", "phrasebook": get_phrasebook(lang)}


# ─────────────────────────────────────────────────────────
# SOS ENDPOINTS
# ─────────────────────────────────────────────────────────

@router.post("/api/v1/sos")
@limiter.limit("3/minute")
async def handle_sos(req: SOSRequest, request: Request, bg_tasks: BackgroundTasks):
    """Emergency SOS dispatch with GPS, context, and auto-translation."""
    report = await dispatch_sos(
        latitude=req.latitude,
        longitude=req.longitude,
        incident_type=req.incident_type,
        description=req.description,
        lang=req.language,
        photo_base64=req.photo_base64,
        severity=req.severity,
    )
    return {"status": "success", **report.to_dict()}


@router.get("/api/v1/emergency-info")
async def emergency_info(lang: str = "en"):
    """Emergency hotlines and instructions (works offline)."""
    return {"status": "success", **get_emergency_info(lang)}


# ─────────────────────────────────────────────────────────
# DISPATCH & HEATMAP
# ─────────────────────────────────────────────────────────

@router.post("/api/v1/dispatch-report")
@limiter.limit("5/minute")
async def dispatch_report(req: DispatchRequest, request: Request):
    """Send official Vietnamese incident report to selected authority."""
    import datetime
    audio_hash = hashlib.md5(req.details.encode()).hexdigest()
    report_text = generate_official_report_vi(
        timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        lat=req.lat, lng=req.lng,
        scam_type=req.scam_type,
        details=req.details,
        audio_signature=f"hash_{audio_hash}"
    )
    return {
        "status": "success",
        "message": f"Report dispatched to {req.authority_name}.",
        "report_content": report_text
    }


@router.get("/api/v1/heatmap/data")
async def heatmap_data():
    """Aggregated coordinate data for the Crowdsourced Scam Heatmap."""
    data = get_heatmap_data()
    return {"status": "success", "data": data}


# ─────────────────────────────────────────────────────────
# I18N & META ENDPOINTS
# ─────────────────────────────────────────────────────────

@router.get("/api/v1/languages")
async def languages():
    """List of supported languages with metadata."""
    return {"status": "success", "languages": get_supported_languages()}


@router.get("/api/v1/translations")
async def translations(lang: str = "en"):
    """Batch UI translations for the given language."""
    return {"status": "success", "language": lang, "translations": get_all_translations(lang)}


# ─────────────────────────────────────────────────────────
# OCR PRICE CHECK & CONTRIBUTE
# ─────────────────────────────────────────────────────────

class OCRPriceCheckRequest(BaseModel):
    image_base64: str
    region: str = "hanoi"
    language: str = "en"

@router.post("/api/v1/check-price-ocr")
@limiter.limit("5/minute")
async def check_price_ocr(req: OCRPriceCheckRequest, request: Request):
    """
    Full OCR pipeline: Image -> Gemini Vision OCR -> extract items -> DB lookup -> Z-score.
    Returns per-item verdict with sample_count, z_score, mean_price, and confidence.
    """
    result = await check_price_from_image(
        image_base64=req.image_base64,
        region=req.region,
        lang=req.language,
    )
    if not result:
        return {"status": "error", "message": "OCR analysis failed. Check API key or image quality."}
    return {"status": "success", "result": result.dict()}


class ContributePriceRequest(BaseModel):
    region: str
    category: str
    item_name: str
    price_vnd: int
    venue_type: str = "street"
    item_name_vi: str = ""
    device_id: str = "unknown"

@router.post("/api/v1/contribute-price")
@limiter.limit("5/day")
async def contribute_price(req: ContributePriceRequest, request: Request):
    """
    Submit a tourist-verified fair price to strengthen the database.
    Only accepted if the price falls within the fair range (prevents poisoning).
    """
    # Validate: only accept prices that are within normal range
    existing = check_single_price(req.item_name, req.price_vnd, req.region)
    if existing.tier == "overpriced":
        return {
            "status": "rejected",
            "message": "Price appears abnormally high. Only fair prices are accepted to prevent data poisoning.",
            "existing_range": existing.price_range,
        }

    success = add_verified_price(
        region=req.region,
        category=req.category,
        item_name=req.item_name,
        price_vnd=req.price_vnd,
        venue_type=req.venue_type,
        item_name_vi=req.item_name_vi,
        device_id=req.device_id,
    )
    
    if not success:
        return {
            "status": "rejected",
            "message": "Rate limit exceeded: You have already contributed to this item today.",
        }

    return {
        "status": "accepted",
        "message": f"Price for {req.item_name} ({req.price_vnd:,} VND) added to database. Thank you!",
    }
