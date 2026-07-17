from fastapi import APIRouter, File, UploadFile, Form, BackgroundTasks
from pydantic import BaseModel
import os
import hashlib
from typing import Optional

from app.engine.price_checker import analyze_price_context
from app.engine.scam_detector import detect_scam_with_ai
from app.engine.defense_scripts import generate_defense_script
from app.engine.blackbox import log_incident, get_heatmap_data
from app.engine.vision_analyzer import analyze_menu_layout
from app.engine.authority_router import find_nearest_authority, generate_official_report_vi
from app.i18n.translations import t

router = APIRouter()

class SituationRequest(BaseModel):
    description: str
    location: str
    language: str = "en"
    lat: float = 21.0285 # Default Hoan Kiem for demo
    lng: float = 105.8542

@router.post("/api/v1/analyze-situation")
async def analyze_situation(req: SituationRequest, background_tasks: BackgroundTasks):
    """
    Advanced Endpoint: Processes a situation description and returns Context-Aware 
    Pricing assessment, Scam detection, and Defense scripts.
    Automatically triggers Guardian Blackbox on extreme overcharges.
    """
    # 1. Price Context & Markup Analysis
    price_assessment = await analyze_price_context(
        description=req.description,
        location_context=req.location,
        lang=req.language
    )
    
    # 2. General Scam Detection
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
        
        # Generate defense script if needed
        script = generate_defense_script(
            tier=price_assessment.tier,
            typology=price_assessment.typology_match,
            fair_price=price_assessment.max_fair_price * (1 if 'quantity' not in req.description else 1),
            asked_price=price_assessment.unit_price,
            item_name=price_assessment.item_name
        )
        response_data["active_defense_script"] = script
        
        # 3. TRIGGER GUARDIAN BLACKBOX FOR SEVERE INCIDENTS
        if price_assessment.tier == "EXTREME_OVERCHARGE":
            response_data["blackbox_triggered"] = True
            
            # Find nearest authority
            nearest_auth, dist_km = find_nearest_authority(req.lat, req.lng)
            if nearest_auth:
                response_data["nearest_authority"] = {
                    "name": nearest_auth.name,
                    "distance_km": round(dist_km, 2),
                    "phone": nearest_auth.phone
                }
            
            # Log to blackbox in background
            audio_hash = hashlib.md5(req.description.encode()).hexdigest()
            background_tasks.add_task(
                log_incident,
                lat=req.lat,
                lng=req.lng,
                severity="CRITICAL",
                scam_type=price_assessment.typology_match or "Severe Overcharge",
                audio_signature=f"hash_{audio_hash}"
            )
            
    return response_data

class DispatchRequest(BaseModel):
    lat: float
    lng: float
    scam_type: str
    details: str
    authority_name: str

@router.post("/api/v1/dispatch-report")
async def dispatch_report(req: DispatchRequest):
    """
    Simulates sending the official Vietnamese incident report to the selected authority.
    """
    import datetime
    audio_hash = hashlib.md5(req.details.encode()).hexdigest()
    
    report_text = generate_official_report_vi(
        timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        lat=req.lat,
        lng=req.lng,
        scam_type=req.scam_type,
        details=req.details,
        audio_signature=f"hash_{audio_hash}"
    )
    
    # In reality, this would send an email/API call to the authority's system.
    # For now, we print it to console and return success.
    print(f"\n--- DISPATCHED TO {req.authority_name.upper()} ---")
    print(report_text)
    print("------------------------------------------\n")
    
    return {
        "status": "success",
        "message": f"Report securely dispatched to {req.authority_name}.",
        "report_content": report_text
    }

@router.get("/api/v1/heatmap/data")
async def heatmap_data():
    """
    Returns aggregated coordinate data for the Crowdsourced Scam Heatmap.
    """
    data = get_heatmap_data()
    return {"status": "success", "data": data}

class VisionRequest(BaseModel):
    image_base64: str
    language: str = "en"

@router.post("/api/v1/analyze-vision")
async def analyze_vision(req: VisionRequest):
    """
    Real endpoint to process Base64 images with Gemini Vision.
    """
    vision_assessment = await analyze_menu_layout(
        image_base64=req.image_base64, 
        mime_type="image/jpeg", 
        lang=req.language
    )
    
    if not vision_assessment:
        return {"status": "error", "message": "Failed to analyze image or API key missing."}
        
    return {
        "status": "success",
        "vision_assessment": vision_assessment.dict()
    }
