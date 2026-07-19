import html
import time

import httpx

from app.core.config import settings
from app.engine.translator import translate_text as translate_with_gemini


GOOGLE_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"
MYMEMORY_TRANSLATE_URL = "https://api.mymemory.translated.net/get"

GOOGLE_LANG_MAP = {
    "en": "en",
    "vi": "vi",
    "ko": "ko",
    "zh": "zh-CN",
    "ru": "ru",
}

MYMEMORY_LANG_MAP = {
    "en": "en",
    "vi": "vi",
    "ko": "ko",
    "zh": "zh",
    "ru": "ru",
}


def _base_result(text: str, provider: str, started_at: float, error: str = "") -> dict:
    return {
        "translation": text,
        "provider": provider,
        "latency_ms": round((time.perf_counter() - started_at) * 1000),
        "romanization": "",
        "cultural_note": "",
        "error": error,
    }


async def _translate_google(text: str, source_lang: str, target_lang: str) -> dict:
    started_at = time.perf_counter()
    if not settings.GOOGLE_TRANSLATE_API_KEY:
        return _base_result(text, "google", started_at, "GOOGLE_TRANSLATE_API_KEY is not configured")

    payload = {
        "q": text,
        "source": GOOGLE_LANG_MAP.get(source_lang, source_lang),
        "target": GOOGLE_LANG_MAP.get(target_lang, target_lang),
        "format": "text",
    }

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(
                GOOGLE_TRANSLATE_URL,
                params={"key": settings.GOOGLE_TRANSLATE_API_KEY},
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        translated = data["data"]["translations"][0]["translatedText"]
        return {
            "translation": html.unescape(translated),
            "provider": "google",
            "latency_ms": round((time.perf_counter() - started_at) * 1000),
            "romanization": "",
            "cultural_note": "",
            "error": "",
        }
    except Exception as exc:
        return _base_result(text, "google", started_at, str(exc))


async def _translate_mymemory(text: str, source_lang: str, target_lang: str) -> dict:
    started_at = time.perf_counter()
    params = {
        "q": text,
        "langpair": (
            f"{MYMEMORY_LANG_MAP.get(source_lang, source_lang)}|"
            f"{MYMEMORY_LANG_MAP.get(target_lang, target_lang)}"
        ),
        "mt": "1",
    }
    if settings.MYMEMORY_EMAIL:
        params["de"] = settings.MYMEMORY_EMAIL

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.get(MYMEMORY_TRANSLATE_URL, params=params)
            response.raise_for_status()

        data = response.json()
        response_status = str(data.get("responseStatus", ""))
        translated = data.get("responseData", {}).get("translatedText", "")
        if response_status != "200" or not translated:
            error = data.get("responseDetails") or f"MyMemory responseStatus={response_status}"
            return _base_result(text, "mymemory", started_at, error)

        return {
            "translation": html.unescape(translated),
            "provider": "mymemory",
            "latency_ms": round((time.perf_counter() - started_at) * 1000),
            "romanization": "",
            "cultural_note": "",
            "error": "",
        }
    except Exception as exc:
        return _base_result(text, "mymemory", started_at, str(exc))


async def translate_realtime(
    text: str,
    source_lang: str,
    target_lang: str,
    context: str = "casual",
) -> dict:
    started_at = time.perf_counter()

    if not text.strip():
        return _base_result("", settings.TRANSLATION_PROVIDER, started_at, "")

    if source_lang == target_lang:
        return _base_result(text, "identity", started_at, "")

    if settings.TRANSLATION_PROVIDER == "google":
        google_result = await _translate_google(text, source_lang, target_lang)
        if not google_result["error"]:
            return google_result
        if not settings.GOOGLE_TRANSLATE_API_KEY:
            return google_result

        gemini_result = await translate_with_gemini(text, source_lang, target_lang, context)
        gemini_result.setdefault("translation", text)
        gemini_result.setdefault("romanization", "")
        gemini_result.setdefault("cultural_note", "")
        gemini_result["provider"] = "gemini_fallback"
        gemini_result["latency_ms"] = round((time.perf_counter() - started_at) * 1000)
        gemini_result["error"] = google_result["error"]
        return gemini_result

    if settings.TRANSLATION_PROVIDER == "mymemory":
        return await _translate_mymemory(text, source_lang, target_lang)

    gemini_result = await translate_with_gemini(text, source_lang, target_lang, context)
    gemini_result.setdefault("translation", text)
    gemini_result.setdefault("romanization", "")
    gemini_result.setdefault("cultural_note", "")
    gemini_result["provider"] = "gemini"
    gemini_result["latency_ms"] = round((time.perf_counter() - started_at) * 1000)
    gemini_result.setdefault("error", "")
    return gemini_result
