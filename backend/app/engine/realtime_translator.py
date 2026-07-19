import html
import re
import time
import unicodedata

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

DEMO_PHRASEBOOK = {
    ("vi", "en"): {
        "30 nghin dong mot chiec banh mi": "30,000 VND for one banh mi.",
        "ba muoi nghin dong mot chiec banh mi": "30,000 VND for one banh mi.",
        "30 nghin dong mot cai banh mi": "30,000 VND for one banh mi.",
        "30 nghin dong mot o banh mi": "30,000 VND for one banh mi.",
        "gia nay da la gia tot roi": "This is already a good price.",
        "gia nay la gia tot roi": "This is already a good price.",
        "duoc toi ban cho ban hai muoi nghin": "Okay, I can sell it to you for 20,000 VND.",
        "duoc toi ban hai muoi nghin": "Okay, I can sell it to you for 20,000 VND.",
    },
    ("vi", "ko"): {
        "30 nghin dong mot chiec banh mi": "반미 하나에 30,000동입니다.",
        "ba muoi nghin dong mot chiec banh mi": "반미 하나에 30,000동입니다.",
        "30 nghin dong mot cai banh mi": "반미 하나에 30,000동입니다.",
        "30 nghin dong mot o banh mi": "반미 하나에 30,000동입니다.",
        "gia nay da la gia tot roi": "이미 좋은 가격입니다.",
        "gia nay la gia tot roi": "이미 좋은 가격입니다.",
        "duoc toi ban cho ban hai muoi nghin": "좋아요, 20,000동에 드릴게요.",
        "duoc toi ban hai muoi nghin": "좋아요, 20,000동에 드릴게요.",
    },
    ("vi", "zh"): {
        "30 nghin dong mot chiec banh mi": "一个越南法棍是30,000越南盾。",
        "ba muoi nghin dong mot chiec banh mi": "一个越南法棍是30,000越南盾。",
        "30 nghin dong mot cai banh mi": "一个越南法棍是30,000越南盾。",
        "30 nghin dong mot o banh mi": "一个越南法棍是30,000越南盾。",
        "gia nay da la gia tot roi": "这已经是很好的价格了。",
        "gia nay la gia tot roi": "这已经是很好的价格了。",
        "duoc toi ban cho ban hai muoi nghin": "好的，我可以卖给你20,000越南盾。",
        "duoc toi ban hai muoi nghin": "好的，我可以卖给你20,000越南盾。",
    },
    ("vi", "ru"): {
        "30 nghin dong mot chiec banh mi": "Один бань ми стоит 30 000 донгов.",
        "ba muoi nghin dong mot chiec banh mi": "Один бань ми стоит 30 000 донгов.",
        "30 nghin dong mot cai banh mi": "Один бань ми стоит 30 000 донгов.",
        "30 nghin dong mot o banh mi": "Один бань ми стоит 30 000 донгов.",
        "gia nay da la gia tot roi": "Это уже хорошая цена.",
        "gia nay la gia tot roi": "Это уже хорошая цена.",
        "duoc toi ban cho ban hai muoi nghin": "Хорошо, я продам вам за 20 000 донгов.",
        "duoc toi ban hai muoi nghin": "Хорошо, я продам вам за 20 000 донгов.",
    },
    ("en", "vi"): {
        "how much is one banh mi": "Một chiếc bánh mì bao nhiêu tiền?",
        "can you lower the price": "Bạn có thể giảm giá không?",
        "can you sell it for twenty thousand dong": "Bạn có thể bán giá hai mươi nghìn đồng không?",
        "that is too expensive": "Giá này quá đắt.",
    },
}


def _normalize_demo_text(text: str) -> str:
    lowered = text.lower()
    without_marks = unicodedata.normalize("NFD", lowered)
    without_marks = "".join(
        char for char in without_marks if unicodedata.category(char) != "Mn"
    )
    without_marks = without_marks.replace("đ", "d")
    without_marks = re.sub(r"[^a-z0-9]+", " ", without_marks)
    return re.sub(r"\s+", " ", without_marks).strip()


def _base_result(text: str, provider: str, started_at: float, error: str = "") -> dict:
    return {
        "translation": text,
        "provider": provider,
        "latency_ms": round((time.perf_counter() - started_at) * 1000),
        "romanization": "",
        "cultural_note": "",
        "error": error,
    }


def _translate_demo_phrasebook(
    text: str,
    source_lang: str,
    target_lang: str,
    started_at: float,
) -> dict | None:
    if not getattr(settings, "ENABLE_DEMO_TRANSLATION", True):
        return None

    normalized = _normalize_demo_text(text)
    translation = DEMO_PHRASEBOOK.get((source_lang, target_lang), {}).get(normalized)
    if not translation:
        return None

    result = _base_result(translation, "demo_phrasebook", started_at, "")
    result["cultural_note"] = "Fixed demo phrasebook match."
    return result


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

    demo_result = _translate_demo_phrasebook(text, source_lang, target_lang, started_at)
    if demo_result:
        return demo_result

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
