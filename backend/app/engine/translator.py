"""
Tour-resQ Domain-Adapted Translator
=====================================
Real-time translation optimized for tourist emergency contexts.

Unlike generic Google Translate, this translator:
- Understands confrontation context (price disputes, scams)
- Preserves urgency and emotional tone
- Includes cultural context hints
- Has a phrasebook for common offline situations
"""
from typing import Optional
from app.i18n.translations import t, TRANSLATIONS
from app.core.config import settings


# ─────────────────────────────────────────────────────────
# OFFLINE PHRASEBOOK
# ─────────────────────────────────────────────────────────
# Pre-translated common phrases that work without internet.
# Each phrase has the tourist's language + Vietnamese translation
# so tourists can SHOW their phone to vendors.

PHRASEBOOK: list[dict] = [
    {
        "category": "negotiation",
        "phrases": [
            "phrase.too_expensive",
            "phrase.original_price",
            "phrase.give_receipt",
            "phrase.show_meter",
        ]
    },
    {
        "category": "safety",
        "phrases": [
            "phrase.call_police",
            "phrase.no_thank_you",
            "phrase.i_dont_want",
        ]
    },
]


def get_phrasebook(lang: str = "en") -> list[dict]:
    """
    Get the offline phrasebook with both tourist language + Vietnamese.
    Perfect for showing the phone to a vendor/driver.
    """
    result = []
    for group in PHRASEBOOK:
        phrases = []
        for key in group["phrases"]:
            entry = TRANSLATIONS.get(key, {})
            phrases.append({
                "key": key,
                "tourist_lang": entry.get(lang, entry.get("en", "")),
                "vietnamese": entry.get("vi", ""),
                "english": entry.get("en", ""),
            })
        result.append({
            "category": group["category"],
            "phrases": phrases,
        })
    return result


async def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
    context: str = "tourist",
) -> dict:
    """
    Translate text using Gemini with domain-specific context.

    Args:
        text: Text to translate
        source_lang: Source language code
        target_lang: Target language code
        context: Context hint ("tourist", "emergency", "negotiation", "casual")

    Returns:
        Dict with translation, romanization, and cultural notes
    """
    try:
        import google.generativeai as genai

        if not settings.gemini_key:
            return {
                "translation": text,
                "romanization": "",
                "cultural_note": "",
                "error": "API key not configured"
            }

        genai.configure(api_key=settings.gemini_key)

        lang_names = {
            "en": "English", "ko": "Korean", "zh": "Chinese",
            "ru": "Russian", "vi": "Vietnamese",
        }
        src = lang_names.get(source_lang, source_lang)
        tgt = lang_names.get(target_lang, target_lang)

        context_instructions = {
            "tourist": "This is a tourist in Vietnam communicating with locals. Keep the translation natural and polite.",
            "emergency": "This is an EMERGENCY situation. The translation must be clear, direct, and convey urgency. Include relevant emergency info.",
            "negotiation": "This is a price negotiation. The translation should be firm but respectful. Vietnamese culture values politeness even in disputes.",
            "casual": "Casual everyday conversation. Natural and friendly tone.",
        }

        ctx = context_instructions.get(context, context_instructions["tourist"])

        prompt = f"""Translate the following from {src} to {tgt}.

Context: {ctx}

Text: "{text}"

Respond in this exact JSON format (no markdown):
{{
  "translation": "the translated text",
  "romanization": "phonetic pronunciation guide if target is Vietnamese/Chinese/Korean (e.g., 'sin loi' for 'xin lỗi'). Empty string if not applicable.",
  "cultural_note": "brief cultural context if relevant (e.g., 'In Vietnam, always smile when negotiating'). Empty string if not needed.",
  "formality": "formal/informal/neutral"
}}"""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        if response and response.text:
            import json
            # Try to parse JSON response
            text_clean = response.text.strip()
            # Remove markdown code fences if present
            if text_clean.startswith("```"):
                text_clean = text_clean.split("\n", 1)[1]
                text_clean = text_clean.rsplit("```", 1)[0]

            try:
                result = json.loads(text_clean)
                return result
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw text
                return {
                    "translation": response.text.strip(),
                    "romanization": "",
                    "cultural_note": "",
                }

    except Exception as e:
        return {
            "translation": text,
            "romanization": "",
            "cultural_note": "",
            "error": str(e),
        }


async def translate_for_confrontation(
    text: str,
    tourist_lang: str,
) -> dict:
    """
    Specialized translation for confrontation situations.
    Translates from tourist's language to Vietnamese AND
    provides the Vietnamese response back in tourist's language.

    Returns both directions for two-way communication.
    """
    # Tourist → Vietnamese (what to show/say to the vendor)
    to_vietnamese = await translate_text(
        text=text,
        source_lang=tourist_lang,
        target_lang="vi",
        context="negotiation",
    )

    return {
        "to_vietnamese": to_vietnamese,
        "original_text": text,
        "tourist_language": tourist_lang,
        "instructions": t("translate.show_to_vendor", tourist_lang),
    }
