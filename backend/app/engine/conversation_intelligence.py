import json
import re

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from app.core.config import settings


class LiveMessageInsight(BaseModel):
    intent: str = Field(default="unknown")
    item_name: str = Field(default="")
    item_name_vi: str = Field(default="")
    price_vnd: int = Field(default=0)
    quantity: float = Field(default=1.0)
    risk_level: str = Field(default="none")
    scam_type: str = Field(default="")
    confidence: float = Field(default=0.0)
    should_alert: bool = Field(default=False)
    should_promote_to_price_db: bool = Field(default=False)
    summary: str = Field(default="")


def _extract_price_vnd(text: str) -> int:
    normalized = text.lower().replace(",", "").replace(".", "")
    match_k = re.search(r"(\d+(?:\.\d+)?)\s*k\b", normalized)
    if match_k:
        return int(float(match_k.group(1)) * 1000)

    match_vnd = re.search(r"(\d{4,})\s*(vnd|dong|đồng|₫)?", normalized)
    if match_vnd:
        return int(match_vnd.group(1))

    return 0


def _fallback_insight(original_text: str, translated_text: str) -> LiveMessageInsight:
    combined = f"{original_text} {translated_text}".lower()
    price_vnd = _extract_price_vnd(combined)
    is_price = price_vnd > 0 or any(
        word in combined
        for word in ["price", "cost", "bao nhiêu", "giá", "tiền"]
    )
    is_suspicious = any(
        word in combined
        for word in ["scam", "fake", "police", "ép", "lừa", "too expensive", "overcharge"]
    )

    if is_suspicious:
        risk_level = "high"
    elif price_vnd >= 300000:
        risk_level = "medium"
    else:
        risk_level = "none"

    return LiveMessageInsight(
        intent="price_discussion" if is_price else "conversation",
        price_vnd=price_vnd,
        risk_level=risk_level,
        scam_type="possible_overcharge" if price_vnd >= 300000 else "",
        confidence=0.55 if is_price else 0.3,
        should_alert=is_suspicious or price_vnd >= 300000,
        should_promote_to_price_db=False,
        summary="Potential price discussion detected." if is_price else "",
    )


async def analyze_live_message(
    original_text: str,
    translated_text: str,
    source_lang: str,
    target_lang: str,
    speaker: str,
    region: str,
    recent_context: list[dict],
) -> LiveMessageInsight:
    if not settings.gemini_key:
        return _fallback_insight(original_text, translated_text)

    context_text = "\n".join(
        f"{row.get('speaker', 'unknown')}: {row.get('original_text', '')} -> {row.get('translated_text', '')}"
        for row in recent_context[-5:]
    )

    prompt = f"""Analyze one live tourist-vendor utterance in Vietnam.

Recent context:
{context_text}

Current utterance:
speaker: {speaker}
source_lang: {source_lang}
target_lang: {target_lang}
region: {region}
original_text: {original_text}
translated_text: {translated_text}

Rules:
1. Extract a price only if it is explicitly spoken.
2. Convert 500k to 500000 VND.
3. Do not mark suspicious or overcharge prices as fair market prices.
4. should_promote_to_price_db must be true only when the phrase clearly describes a normal paid price, not a complaint, threat, or scam.
5. Keep item_name in simple English, item_name_vi in Vietnamese if clear.

Return JSON only."""

    try:
        client = genai.Client(api_key=settings.gemini_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LiveMessageInsight,
                temperature=0.1,
            ),
        )
        if not response.text:
            return _fallback_insight(original_text, translated_text)

        insight = LiveMessageInsight(**json.loads(response.text))
        if insight.confidence < settings.LIVE_ANALYSIS_MIN_CONFIDENCE:
            insight.should_promote_to_price_db = False
        if insight.risk_level in ("medium", "high"):
            insight.should_promote_to_price_db = False
        return insight
    except Exception:
        return _fallback_insight(original_text, translated_text)
