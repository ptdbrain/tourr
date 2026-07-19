from fastapi.testclient import TestClient

from main import app
from app.api import live_negotiation
from app.data import price_db


def test_live_message_returns_fast_translation(monkeypatch):
    async def fake_translate_realtime(text, source_lang, target_lang, context):
        return {
            "translation": "How much is this?",
            "provider": "google",
            "latency_ms": 12,
            "romanization": "",
            "cultural_note": "",
            "error": "",
        }

    async def fake_analyze_and_store_message(**kwargs):
        return None

    monkeypatch.setattr(live_negotiation, "translate_realtime", fake_translate_realtime)
    monkeypatch.setattr(live_negotiation, "analyze_and_store_message", fake_analyze_and_store_message)

    client = TestClient(app)
    start = client.post("/api/v1/live/start").json()
    response = client.post("/api/v1/live/message", json={
        "session_id": start["session_id"],
        "text": "Cai nay bao nhieu tien?",
        "source_lang": "vi",
        "target_lang": "en",
        "speaker": "vendor",
        "region": "hanoi",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["translated"] == "How much is this?"
    assert body["provider"] == "google"
    assert body["analysis_status"] == "queued"
    assert body["price_alert"]["should_alert"] is False


def test_live_message_returns_realtime_price_alert(monkeypatch):
    async def fake_translate_realtime(text, source_lang, target_lang, context):
        return {
            "translation": "30 thousand dong for one cake",
            "provider": "mymemory",
            "latency_ms": 15,
            "romanization": "",
            "cultural_note": "",
            "error": "",
        }

    async def fake_analyze_and_store_message(**kwargs):
        return None

    def fake_detect_realtime_price_alert(original_text, translated_text, region):
        return {
            "should_alert": True,
            "reason": "above_median",
            "tier": "above_median",
            "item_name": "banh_mi",
            "item_label": "banh mi",
            "asked_price": 30000,
            "unit_price": 30000,
            "quantity": 1,
            "median_price": 25000,
            "price_range": "15,000 - 45,000 VND",
            "sample_count": 5,
            "confidence": 0.25,
            "message": "30,000 VND may be higher than the usual 25,000 VND for 1 banh mi in hanoi.",
        }

    monkeypatch.setattr(live_negotiation, "translate_realtime", fake_translate_realtime)
    monkeypatch.setattr(live_negotiation, "analyze_and_store_message", fake_analyze_and_store_message)
    monkeypatch.setattr(live_negotiation, "detect_realtime_price_alert", fake_detect_realtime_price_alert, raising=False)

    client = TestClient(app)
    start = client.post("/api/v1/live/start").json()
    response = client.post("/api/v1/live/message", json={
        "session_id": start["session_id"],
        "text": "30 nghin dong mot chiec banh",
        "source_lang": "vi",
        "target_lang": "en",
        "speaker": "vendor",
        "region": "hanoi",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["price_alert"]["should_alert"] is True
    assert body["price_alert"]["item_name"] == "banh_mi"
    assert "30,000 VND" in body["price_alert"]["message"]


def test_live_message_demo_phrasebook_keeps_price_alert(monkeypatch):
    from app.engine import realtime_translator

    monkeypatch.setattr(live_negotiation.settings, "ENABLE_LIVE_AI_ANALYSIS", False)
    monkeypatch.setattr(realtime_translator.settings, "ENABLE_DEMO_TRANSLATION", True, raising=False)
    monkeypatch.setattr(realtime_translator.settings, "TRANSLATION_PROVIDER", "mymemory")

    client = TestClient(app)
    start = client.post("/api/v1/live/start").json()
    response = client.post("/api/v1/live/message", json={
        "session_id": start["session_id"],
        "text": "30 nghin dong mot chiec banh mi",
        "source_lang": "vi",
        "target_lang": "en",
        "speaker": "vendor",
        "region": "hanoi",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["translated"] == "30,000 VND for one banh mi."
    assert body["provider"] == "demo_phrasebook"
    assert body["translation_error"] == ""
    assert body["analysis_status"] == "disabled"
    assert body["price_alert"]["should_alert"] is True
    assert body["price_alert"]["item_name"] == "banh_mi"


def test_live_observation_can_be_edited_from_api(tmp_path, monkeypatch):
    monkeypatch.setattr(price_db, "DB_PATH", str(tmp_path / "tour_resq_test.db"))
    price_db.init_price_db()
    observation_id = price_db.add_conversation_observation(
        session_id="editable-session",
        message_id="editable-message",
        region="hanoi",
        speaker="vendor",
        source_lang="vi",
        target_lang="en",
        original_text_scrubbed="ban pho 500k",
        translated_text="sell pho for 500k",
        intent="price_quote",
        item_name="pho",
        item_name_vi="phở",
        price_vnd=500000,
        quantity=1.0,
        risk_level="high",
        scam_type="overcharge",
        confidence=0.9,
        should_alert=True,
        should_promote_to_price_db=False,
    )

    client = TestClient(app)
    response = client.patch(f"/api/v1/live/observations/{observation_id}", json={
        "item_name": "bun_cha",
        "item_name_vi": "bún chả",
        "price_vnd": 90000,
        "risk_level": "medium",
    })

    assert response.status_code == 200
    assert response.json()["updated"] is True

    rows = price_db.get_recent_session_observations("editable-session", limit=1)
    assert rows[0]["item_name"] == "bun_cha"
    assert rows[0]["item_name_vi"] == "bún chả"
    assert rows[0]["price_vnd"] == 90000
