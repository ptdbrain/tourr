from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
import datetime
import json
import re
from google import genai
from google.genai import types

from app.engine.translator import translate_text
from app.engine.realtime_translator import translate_realtime
from app.engine.conversation_intelligence import analyze_live_message
from app.engine.realtime_price_guard import detect_realtime_price_alert
from app.engine.privacy_scrubber import scrub_pii
from app.core.config import settings
from app.data.price_db import (
    add_conversation_observation,
    get_recent_session_observations,
    update_conversation_observation,
    verify_conversation_observation,
)

router = APIRouter()

# In-memory storage for live sessions to ensure maximum speed during demo
# Structure: { session_id: [ {"speaker": "tourist", "text": "...", "translated": "...", "timestamp": "..."} ] }
active_sessions: Dict[str, List[dict]] = {}

class LiveMessageRequest(BaseModel):
    session_id: str
    text: str
    source_lang: str
    target_lang: str
    speaker: str  # "tourist" or "vendor"
    region: str = "hanoi"

class LiveConcludeRequest(BaseModel):
    session_id: str
    tourist_lang: str = "en"
    region: str = "hanoi"  # Used for ambient data context

class LiveObservationUpdateRequest(BaseModel):
    region: Optional[str] = None
    speaker: Optional[str] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    original_text_scrubbed: Optional[str] = None
    translated_text: Optional[str] = None
    intent: Optional[str] = None
    item_name: Optional[str] = None
    item_name_vi: Optional[str] = None
    price_vnd: Optional[int] = None
    quantity: Optional[float] = None
    risk_level: Optional[str] = None
    scam_type: Optional[str] = None
    confidence: Optional[float] = None
    should_alert: Optional[bool] = None
    should_promote_to_price_db: Optional[bool] = None
    is_verified: Optional[bool] = None

@router.post("/api/v1/live/start")
async def start_session():
    """Start a new live negotiation session and return its ID."""
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = []
    return {"status": "success", "session_id": session_id}

async def analyze_and_store_message(
    session_id: str,
    message_id: str,
    original_text: str,
    translated_text: str,
    source_lang: str,
    target_lang: str,
    speaker: str,
    region: str,
    recent_context: list[dict],
) -> None:
    """Analyze live speech outside the translation path and store editable observations."""
    insight = await analyze_live_message(
        original_text=original_text,
        translated_text=translated_text,
        source_lang=source_lang,
        target_lang=target_lang,
        speaker=speaker,
        region=region,
        recent_context=recent_context,
    )

    add_conversation_observation(
        session_id=session_id,
        message_id=message_id,
        region=region,
        speaker=speaker,
        source_lang=source_lang,
        target_lang=target_lang,
        original_text_scrubbed=original_text,
        translated_text=translated_text,
        intent=insight.intent,
        item_name=insight.item_name,
        item_name_vi=insight.item_name_vi,
        price_vnd=insight.price_vnd,
        quantity=insight.quantity,
        risk_level=insight.risk_level,
        scam_type=insight.scam_type,
        confidence=insight.confidence,
        should_alert=insight.should_alert,
        should_promote_to_price_db=insight.should_promote_to_price_db,
    )

@router.post("/api/v1/live/message")
async def process_live_message(req: LiveMessageRequest, bg_tasks: BackgroundTasks):
    """
    Process a single message in real-time. 
    Focuses entirely on low-latency translation and buffers the transcript.
    """
    if req.session_id not in active_sessions:
        active_sessions[req.session_id] = []

    safe_text = scrub_pii(req.text)
    
    # Context hint based on speaker
    context = "negotiation" if req.speaker == "tourist" else "casual"

    message_id = str(uuid.uuid4())
    translation_result = await translate_realtime(
        text=safe_text,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
        context=context
    )
    
    translated_text = translation_result.get("translation", "")

    # Buffer for final analysis
    active_sessions[req.session_id].append({
        "message_id": message_id,
        "speaker": req.speaker,
        "original_text": safe_text,
        "translated_text": translated_text,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
    })

    if settings.ENABLE_LIVE_AI_ANALYSIS:
        bg_tasks.add_task(
            analyze_and_store_message,
            session_id=req.session_id,
            message_id=message_id,
            original_text=safe_text,
            translated_text=translated_text,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
            speaker=req.speaker,
            region=req.region,
            recent_context=active_sessions[req.session_id][-5:],
        )
        analysis_status = "queued"
    else:
        analysis_status = "disabled"

    combined_text = (safe_text + " " + translated_text).lower()
    is_price_discussion = bool(re.search(r'\d+|price|cost|money|vnd|dong|bao nhiêu|tiền|giá|đắt', combined_text))
    is_suspicious = bool(re.search(r'police|fake|scam|lừa|cảnh sát|bắt|đóng cửa|không mua|ép|đánh|chết', combined_text))

    price_alert = detect_realtime_price_alert(
        original_text=safe_text,
        translated_text=translated_text,
        region=req.region,
    )

    return {
        "status": "success",
        "message_id": message_id,
        "original": safe_text,
        "translated": translated_text,
        "romanization": translation_result.get("romanization", ""),
        "provider": translation_result.get("provider", ""),
        "translation_latency_ms": translation_result.get("latency_ms", 0),
        "translation_error": translation_result.get("error", ""),
        "analysis_status": analysis_status,
        "is_price_discussion": is_price_discussion,
        "is_suspicious": is_suspicious,
        "price_alert": price_alert
    }


@router.get("/api/v1/live/insights/{session_id}")
async def get_live_insights(session_id: str, limit: int = 5):
    observations = get_recent_session_observations(session_id, limit=limit)
    return {
        "status": "success",
        "session_id": session_id,
        "observations": observations,
    }


@router.patch("/api/v1/live/observations/{observation_id}")
async def update_live_observation(observation_id: int, req: LiveObservationUpdateRequest):
    updates = req.model_dump(exclude_unset=True)
    updated = update_conversation_observation(observation_id, **updates)
    return {
        "status": "success" if updated else "not_found",
        "observation_id": observation_id,
        "updated": updated,
    }


@router.post("/api/v1/live/observations/{observation_id}/verify")
async def verify_live_observation(observation_id: int, should_promote_to_price_db: bool = False):
    verified = verify_conversation_observation(
        observation_id,
        should_promote_to_price_db=should_promote_to_price_db,
    )
    return {
        "status": "success" if verified else "not_found",
        "observation_id": observation_id,
        "verified": verified,
    }


def process_ambient_telemetry(transcript: str, region: str):
    """
    Background task to extract prices passively from conversation logs 
    and save them anonymously to the DB.
    """
    try:
        if not settings.gemini_key:
            return []
        
        prompt = f"""Analyze this scrubbed negotiation transcript.
Extract any mentioned items and their finalized or offered price in VND.
Return ONLY valid JSON in this format:
{{"items": [{{"item_name": "bánh mì", "price_vnd": 30000}}]}}
If no prices or items are clearly mentioned, return {{"items": []}}.
Do not include any other text or markdown.

Transcript:
{transcript}"""

        client = genai.Client(api_key=settings.gemini_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        
        raw_text = response.text.strip().removeprefix('```json').removesuffix('```').strip()
        data = json.loads(raw_text)
        
        return data.get("items", [])
                
    except Exception as e:
        pass # Silently fail background telemetry


@router.post("/api/v1/live/conclude")
async def conclude_live_session(req: LiveConcludeRequest, bg_tasks: BackgroundTasks):
    """
    Conclude the session. Analyzes the entire transcript for scam indicators,
    and runs ambient telemetry extraction in the background.
    """
    if req.session_id not in active_sessions or not active_sessions[req.session_id]:
        return {"status": "error", "message": "Session not found or empty."}

    history = active_sessions[req.session_id]
    
    # Build transcript string
    transcript = ""
    for msg in history:
        role = "Tourist" if msg["speaker"] == "tourist" else "Vendor"
        transcript += f"{role}: {msg['original_text']}\n"

    try:
        lang_names = {"en": "English", "ko": "Korean", "zh": "Chinese", "ru": "Russian"}
        target_lang = lang_names.get(req.tourist_lang, "English")
        if not settings.gemini_key:
            analysis = "Session ended. AI summary is unavailable because GEMINI_API_KEY is not configured."
            del active_sessions[req.session_id]
            return {
                "status": "success",
                "transcript_length": len(history),
                "final_verdict": analysis
            }

        prompt = f"""You are a tourist safety AI assistant in Vietnam.
Analyze the following live negotiation transcript between a tourist and a local vendor.

Transcript:
{transcript}

Analyze the interaction:
1. Is the vendor using pressure tactics, intimidation, or classic scam techniques?
2. If prices were mentioned, do they seem like an extreme overcharge (e.g. 500k VND for a simple meal)?
3. What is your final verdict for the tourist? (e.g. "Safe to buy", "Walk away immediately", "Negotiate lower").

Respond in {target_lang}. Keep it under 60 words. Use bullet points."""

        client = genai.Client(api_key=settings.gemini_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=150,
                temperature=0.2
            )
        )
        
        analysis = response.text.strip() if response and response.text else "Analysis failed."
        
        # Cleanup session to free memory
        del active_sessions[req.session_id]
        
        return {
            "status": "success",
            "transcript_length": len(history),
            "final_verdict": analysis
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
