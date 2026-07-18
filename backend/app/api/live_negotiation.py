from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
import datetime

from app.engine.translator import translate_text
from app.engine.privacy_scrubber import scrub_pii
from app.core.config import settings

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

class LiveConcludeRequest(BaseModel):
    session_id: str
    tourist_lang: str = "en"

@router.post("/api/v1/live/start")
async def start_session():
    """Start a new live negotiation session and return its ID."""
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = []
    return {"status": "success", "session_id": session_id}

@router.post("/api/v1/live/message")
async def process_live_message(req: LiveMessageRequest):
    """
    Process a single message in real-time. 
    Focuses entirely on low-latency translation and buffers the transcript.
    """
    if req.session_id not in active_sessions:
        active_sessions[req.session_id] = []

    safe_text = scrub_pii(req.text)
    
    # Context hint based on speaker
    context = "negotiation" if req.speaker == "tourist" else "casual"

    # Fast translation
    translation_result = await translate_text(
        text=safe_text,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
        context=context
    )
    
    translated_text = translation_result.get("translation", "")

    # Buffer for final analysis
    active_sessions[req.session_id].append({
        "speaker": req.speaker,
        "original_text": safe_text,
        "translated_text": translated_text,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    import re
    combined_text = (safe_text + " " + translated_text).lower()
    is_price_discussion = bool(re.search(r'\d+|price|cost|money|vnd|dong|bao nhiêu|tiền|giá|đắt', combined_text))
    is_suspicious = bool(re.search(r'police|fake|scam|lừa|cảnh sát|bắt|đóng cửa|không mua|ép|đánh|chết', combined_text))

    return {
        "status": "success",
        "original": safe_text,
        "translated": translated_text,
        "romanization": translation_result.get("romanization", ""),
        "is_price_discussion": is_price_discussion,
        "is_suspicious": is_suspicious
    }

@router.post("/api/v1/live/conclude")
async def conclude_live_session(req: LiveConcludeRequest):
    """
    Conclude the session. Analyzes the entire transcript for scam indicators,
    pressure tactics, and price anomalies.
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
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_key)
        
        lang_names = {"en": "English", "ko": "Korean", "zh": "Chinese", "ru": "Russian"}
        target_lang = lang_names.get(req.tourist_lang, "English")

        prompt = f"""You are a tourist safety AI assistant in Vietnam.
Analyze the following live negotiation transcript between a tourist and a local vendor.

Transcript:
{transcript}

Analyze the interaction:
1. Is the vendor using pressure tactics, intimidation, or classic scam techniques?
2. If prices were mentioned, do they seem like an extreme overcharge (e.g. 500k VND for a simple meal)?
3. What is your final verdict for the tourist? (e.g. "Safe to buy", "Walk away immediately", "Negotiate lower").

Respond in {target_lang}. Keep it under 60 words. Use bullet points."""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
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
