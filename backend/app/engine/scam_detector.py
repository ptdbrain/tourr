"""
Tour-resQ Scam Pattern Detector
================================
Detects common tourist scam patterns from text/voice descriptions.

Two-layer approach:
1. Pattern matching: Fast, offline-capable keyword detection
2. AI analysis: Gemini-powered contextual understanding (online)

Common scam patterns specific to Vietnam:
- Taxi meter tampering / long routes
- Menu price switching / no-menu restaurants
- Ghost tours / fake tour operators
- Money exchange scams / counterfeit bills
- Forced services (shoe shine, motorbike wash)
- Gem/jewelry store scams
- Street vendor overcharging
"""
import re
from typing import Optional
from dataclasses import dataclass, asdict, field
from app.i18n.translations import t


@dataclass
class ScamPattern:
    """A known scam pattern with advice."""
    id: str
    name_key: str        # i18n key for pattern name
    advice_key: str      # i18n key for advice
    keywords: list[str]  # Keywords that trigger this pattern (multilingual)
    severity: str        # 'low', 'medium', 'high'
    category: str        # 'transport', 'food', 'tour', 'money', 'service'


@dataclass
class ScamDetectionResult:
    """Result of scam pattern analysis."""
    detected: bool
    patterns: list[dict]
    ai_analysis: str
    advice: list[str]
    severity: str  # highest severity found
    language: str

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────
# SCAM PATTERN LIBRARY
# ─────────────────────────────────────────────────────────
# Keywords include Vietnamese, English, Korean, Chinese, Russian terms

SCAM_PATTERNS: list[ScamPattern] = [
    ScamPattern(
        id="taxi_meter",
        name_key="scam.pattern.taxi_meter",
        advice_key="advice.taxi_meter",
        keywords=[
            # English
            "taxi", "meter", "cab", "driver", "long route", "detour",
            "wrong way", "rigged", "tampered", "fast meter", "broken meter",
            # Vietnamese
            "đồng hồ", "gian lận", "chạy vòng", "đi đường vòng",
            # Korean
            "택시", "미터기", "기사", "돌아가", "바가지",
            # Chinese
            "出租车", "计价器", "绕路", "司机", "打表",
            # Russian
            "такси", "счётчик", "водитель", "объезд", "накрутка",
        ],
        severity="high",
        category="transport",
    ),
    ScamPattern(
        id="overcharge",
        name_key="scam.pattern.overcharge",
        advice_key="advice.overcharge",
        keywords=[
            # English
            "expensive", "overcharge", "too much", "rip off", "cheat",
            "double price", "tourist price", "no receipt", "no menu",
            "hidden fee", "extra charge", "different price",
            # Vietnamese
            "chặt chém", "đắt", "không hóa đơn", "giá du lịch",
            # Korean
            "비싸", "바가지", "관광객 가격", "영수증 없", "속았",
            # Chinese
            "太贵", "宰客", "坑人", "没有菜单", "游客价格", "欺骗",
            # Russian
            "дорого", "обман", "завысили", "нет чека", "обсчитали",
        ],
        severity="medium",
        category="food",
    ),
    ScamPattern(
        id="ghost_tour",
        name_key="scam.pattern.ghost_tour",
        advice_key="advice.ghost_tour",
        keywords=[
            # English
            "tour", "fake tour", "no tour", "cancelled", "different tour",
            "not what promised", "scam tour", "no bus", "not real",
            "paid upfront", "deposit", "no refund",
            # Vietnamese
            "tour ma", "tour giả", "không đúng", "mất tiền", "hủy tour",
            # Korean
            "투어", "사기 투어", "가짜 투어", "취소", "환불",
            # Chinese
            "假旅游", "骗子旅行社", "取消", "不退款", "不存在",
            # Russian
            "фейковый тур", "обман тур", "отмена", "нет возврата",
        ],
        severity="high",
        category="tour",
    ),
    ScamPattern(
        id="money_exchange",
        name_key="scam.pattern.money_exchange",
        advice_key="advice.money_exchange",
        keywords=[
            # English
            "exchange", "money change", "currency", "bad rate", "fake bills",
            "counterfeit", "wrong amount", "short change", "commission",
            # Vietnamese
            "đổi tiền", "tỷ giá", "tiền giả", "thiếu tiền",
            # Korean
            "환전", "환율", "위조", "가짜 돈", "수수료",
            # Chinese
            "换汇", "汇率", "假钱", "假币", "手续费",
            # Russian
            "обмен валюты", "курс", "фальшивые", "подделка", "комиссия",
        ],
        severity="high",
        category="money",
    ),
    ScamPattern(
        id="forced_service",
        name_key="scam.pattern.shoe_shine",
        advice_key="advice.shoe_shine",
        keywords=[
            # English
            "shoe shine", "clean shoes", "forced", "didn't ask",
            "grabbed", "won't let go", "demanding", "aggressive",
            "flower", "bracelet", "massage", "photo",
            # Vietnamese
            "đánh giày", "ép", "cưỡng chế", "bắt trả tiền",
            # Korean
            "구두닦기", "강제", "요구", "안 요청", "공격적",
            # Chinese
            "擦鞋", "强制", "没有要求", "要求付款", "纠缠",
            # Russian
            "чистка обуви", "навязали", "не просил", "агрессивно", "требуют",
        ],
        severity="medium",
        category="service",
    ),
]


def detect_scam_patterns(
    description: str,
    lang: str = "en",
) -> ScamDetectionResult:
    """
    Detect scam patterns from a text description.

    Layer 1: Fast keyword matching (works offline).
    Returns matched patterns with localized advice.

    Args:
        description: User's description of the situation
        lang: Language code for response

    Returns:
        ScamDetectionResult with matched patterns and advice
    """
    description_lower = description.lower()
    matched = []
    advice_list = []
    max_severity = "low"

    severity_rank = {"low": 0, "medium": 1, "high": 2}

    for pattern in SCAM_PATTERNS:
        # Count keyword matches
        match_count = sum(
            1 for kw in pattern.keywords
            if kw.lower() in description_lower
        )

        # Require at least 2 keyword matches to reduce false positives
        if match_count >= 2:
            matched.append({
                "id": pattern.id,
                "name": t(pattern.name_key, lang),
                "severity": pattern.severity,
                "category": pattern.category,
                "match_confidence": min(1.0, match_count / 4),  # 4+ keywords = 100%
            })

            advice_list.append(t(pattern.advice_key, lang))

            if severity_rank.get(pattern.severity, 0) > severity_rank.get(max_severity, 0):
                max_severity = pattern.severity

    detected = len(matched) > 0

    return ScamDetectionResult(
        detected=detected,
        patterns=matched,
        ai_analysis="",  # Will be filled by AI layer if available
        advice=advice_list,
        severity=max_severity if detected else "none",
        language=lang,
    )


async def detect_scam_with_ai(
    description: str,
    lang: str = "en",
    region: str = "hanoi",
) -> ScamDetectionResult:
    """
    Enhanced scam detection using Gemini AI for contextual understanding.

    Layer 2: AI-powered analysis (requires internet).
    Combines keyword results with AI reasoning.
    """
    # First, run pattern matching
    result = detect_scam_patterns(description, lang)

    # Then enhance with AI analysis
    try:
        from google import genai
        from google.genai import types
        from app.core.config import settings

        if not settings.gemini_key:
            return result

        client = genai.Client(api_key=settings.gemini_key)

        from app.engine.privacy_scrubber import scrub_pii
        safe_description = scrub_pii(description)

        lang_names = {"en": "English", "ko": "Korean", "zh": "Chinese", "ru": "Russian"}
        target_lang = lang_names.get(lang, "English")

        prompt = f"""You are a tourist safety AI assistant in Vietnam.

A tourist described this situation:
"{safe_description}"

Location: {region}, Vietnam

Analyze this situation and respond in {target_lang}:
1. Is this a known scam pattern? If yes, which type?
2. What specific advice would you give this tourist RIGHT NOW?
3. Rate the urgency: low / medium / high

Important rules:
- Be empathetic and calming — the tourist may be stressed
- Give SPECIFIC, ACTIONABLE advice for Vietnam
- Include relevant phone numbers (Police: 113, Tourism hotline: 1900-6068)
- Do NOT accuse anyone directly — use phrases like "this situation resembles..."
- Keep response UNDER 40 WORDS. Be extremely concise. Use bullet points.
- Respond entirely in {target_lang}"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=100,
                temperature=0.2
            )
        )

        if response and response.text:
            result.ai_analysis = response.text.strip()

            # If AI detected something but pattern matching didn't
            if not result.detected:
                # Check if AI response suggests a scam
                scam_indicators = [
                    "scam", "fraud", "overcharge", "careful", "caution",
                    "사기", "조심", "주의",
                    "骗", "小心", "注意",
                    "мошенничество", "осторожно", "обман",
                ]
                if any(ind.lower() in response.text.lower() for ind in scam_indicators):
                    result.detected = True
                    result.severity = "medium"

    except Exception as e:
        # AI layer failure is non-critical — pattern matching still works
        result.ai_analysis = ""

    return result
