"""
Tour-resQ SOS Emergency Dispatcher
====================================
Automated emergency dispatch system.

When a tourist triggers SOS:
1. Capture GPS coordinates
2. Package incident context (description, photos, scam type)
3. Dispatch via webhook to control center (Google Sheets)
4. Provide immediate hotline information
5. Generate a pre-written police report in Vietnamese

The webhook approach is deliberate:
- Works without building custom emergency backend
- Google Sheets is accessible to any police/tourism office
- Can be set up in minutes during hackathon
- Proves the concept without infrastructure dependency
"""
import json
import httpx
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, asdict
from loguru import logger

from app.core.config import settings
from app.i18n.translations import t


@dataclass
class SOSReport:
    """Complete SOS dispatch package."""
    report_id: str
    timestamp: str
    # Tourist info
    language: str
    # Location
    latitude: float
    longitude: float
    location_description: str
    # Incident
    incident_type: str  # 'overcharge', 'scam', 'threat', 'theft', 'other'
    description: str
    description_vi: str  # Auto-translated to Vietnamese for police
    severity: str  # 'low', 'medium', 'high', 'critical'
    # Evidence
    photo_base64: str  # Base64 encoded photo if available
    # Status
    dispatch_status: str  # 'pending', 'sent', 'confirmed', 'resolved'
    # Hotlines
    hotlines: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


async def dispatch_sos(
    latitude: float,
    longitude: float,
    incident_type: str = "other",
    description: str = "",
    lang: str = "en",
    photo_base64: str = "",
    severity: str = "high",
) -> SOSReport:
    """
    Dispatch an SOS emergency report.

    Steps:
    1. Generate unique report ID
    2. Translate description to Vietnamese (for police)
    3. Package all info
    4. Send via webhook to control center
    5. Return report with hotline info

    Args:
        latitude, longitude: GPS coordinates
        incident_type: Type of incident
        description: Tourist's description in their language
        lang: Tourist's language code
        photo_base64: Base64 encoded photo (optional)
        severity: Urgency level

    Returns:
        SOSReport with dispatch status and hotline info
    """
    import uuid
    report_id = f"SOS-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    # Translate description to Vietnamese for police
    description_vi = await _translate_for_police(description, lang)

    # Build Google Maps link for location
    maps_link = f"https://maps.google.com/maps?q={latitude},{longitude}"
    location_desc = f"GPS: {latitude:.6f}, {longitude:.6f}\n{maps_link}"

    # Hotlines
    hotlines = [
        {"name": t("sos.call_police", lang), "number": settings.POLICE_HOTLINE},
        {"name": t("sos.call_tourist_hotline", lang), "number": settings.TOURISM_HOTLINE},
        {"name": t("sos.call_tourist_police", lang), "number": settings.TOURIST_POLICE_HOTLINE},
    ]

    report = SOSReport(
        report_id=report_id,
        timestamp=timestamp,
        language=lang,
        latitude=latitude,
        longitude=longitude,
        location_description=location_desc,
        incident_type=incident_type,
        description=description,
        description_vi=description_vi,
        severity=severity,
        photo_base64=photo_base64[:100] + "..." if len(photo_base64) > 100 else photo_base64,
        dispatch_status="pending",
        hotlines=hotlines,
    )

    # Dispatch via webhook
    webhook_success = await _send_webhook(report, photo_base64)
    report.dispatch_status = "sent" if webhook_success else "pending"

    if webhook_success:
        logger.info(f"🚨 SOS dispatched: {report_id} at ({latitude}, {longitude})")
    else:
        logger.warning(f"🚨 SOS webhook failed for {report_id}, hotlines still available")

    return report


async def _translate_for_police(text: str, source_lang: str) -> str:
    """Translate the tourist's description to Vietnamese for the police report."""
    if not text:
        return ""

    if source_lang == "vi":
        return text

    try:
        from app.engine.translator import translate_text
        result = await translate_text(
            text=text,
            source_lang=source_lang,
            target_lang="vi",
            context="emergency",
        )
        return result.get("translation", text)
    except Exception:
        return f"[{source_lang}] {text}"


async def _send_webhook(report: SOSReport, photo_base64: str = "") -> bool:
    """
    Send SOS report to Google Apps Script webhook.
    The webhook inserts a row into Google Sheets for the control center.
    """
    if not settings.SOS_WEBHOOK_URL:
        logger.warning("SOS webhook URL not configured")
        return False

    try:
        payload = {
            "report_id": report.report_id,
            "timestamp": report.timestamp,
            "language": report.language,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "maps_link": f"https://maps.google.com/maps?q={report.latitude},{report.longitude}",
            "incident_type": report.incident_type,
            "description": report.description,
            "description_vi": report.description_vi,
            "severity": report.severity,
            "has_photo": bool(photo_base64),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                settings.SOS_WEBHOOK_URL,
                json=payload,
            )
            return resp.status_code in (200, 201, 302)

    except Exception as e:
        logger.error(f"Webhook dispatch failed: {e}")
        return False


def get_emergency_info(lang: str = "en") -> dict:
    """
    Get all emergency information for display.
    This works offline — no API calls needed.
    """
    return {
        "hotlines": [
            {
                "name": t("sos.call_police", lang),
                "number": settings.POLICE_HOTLINE,
                "icon": "🚔",
            },
            {
                "name": t("sos.call_tourist_hotline", lang),
                "number": settings.TOURISM_HOTLINE,
                "icon": "📞",
            },
            {
                "name": t("sos.call_tourist_police", lang),
                "number": settings.TOURIST_POLICE_HOTLINE,
                "icon": "👮",
            },
        ],
        "instructions": t("sos.stay_calm", lang),
        "share_location": t("sos.share_location", lang),
    }
