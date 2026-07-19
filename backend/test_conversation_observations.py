import uuid

import pytest

from app.data import price_db


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_add_list_update_and_verify_conversation_observation(tmp_path, monkeypatch):
    monkeypatch.setattr(price_db, "DB_PATH", str(tmp_path / "tour_resq_test.db"))
    price_db.init_price_db()
    session_id = f"session-{uuid.uuid4().hex}"
    message_id = f"message-{uuid.uuid4().hex}"

    observation_id = price_db.add_conversation_observation(
        session_id=session_id,
        message_id=message_id,
        region="hanoi",
        speaker="vendor",
        source_lang="vi",
        target_lang="en",
        original_text_scrubbed="Toi ban pho gia 500k",
        translated_text="I sell pho for 500k",
        intent="price_quote",
        item_name="pho",
        item_name_vi="phở",
        price_vnd=500000,
        quantity=1.0,
        risk_level="high",
        scam_type="overcharge",
        confidence=0.91,
        should_alert=True,
        should_promote_to_price_db=False,
    )

    rows = price_db.get_recent_session_observations(session_id, limit=5)

    assert observation_id > 0
    assert len(rows) == 1
    assert rows[0]["message_id"] == message_id
    assert rows[0]["item_name"] == "pho"
    assert rows[0]["price_vnd"] == 500000
    assert rows[0]["should_promote_to_price_db"] == 0

    updated = price_db.update_conversation_observation(
        observation_id,
        item_name="bun_cha",
        item_name_vi="bún chả",
        price_vnd=90000,
        risk_level="medium",
        should_alert=True,
    )
    assert updated is True

    verified = price_db.verify_conversation_observation(
        observation_id,
        should_promote_to_price_db=False,
    )
    assert verified is True

    updated_rows = price_db.get_recent_session_observations(session_id, limit=5)
    assert updated_rows[0]["item_name"] == "bun_cha"
    assert updated_rows[0]["item_name_vi"] == "bún chả"
    assert updated_rows[0]["price_vnd"] == 90000
    assert updated_rows[0]["is_verified"] == 1
    assert updated_rows[0]["should_promote_to_price_db"] == 0


def test_add_conversation_observation_migrates_stale_database(tmp_path, monkeypatch):
    monkeypatch.setattr(price_db, "DB_PATH", str(tmp_path / "stale_tour_resq.db"))

    observation_id = price_db.add_conversation_observation(
        session_id="stale-session",
        message_id="stale-message",
        region="hanoi",
        speaker="vendor",
        source_lang="vi",
        target_lang="en",
        original_text_scrubbed="pho 500k",
        translated_text="pho 500k",
        intent="price_quote",
        item_name="pho",
        item_name_vi="phá»Ÿ",
        price_vnd=500000,
        quantity=1.0,
        risk_level="high",
        scam_type="overcharge",
        confidence=0.9,
        should_alert=True,
        should_promote_to_price_db=False,
    )

    rows = price_db.get_recent_session_observations("stale-session", limit=1)

    assert observation_id > 0
    assert rows[0]["message_id"] == "stale-message"


@pytest.mark.anyio
async def test_analyze_live_message_without_gemini_uses_safe_fallback(monkeypatch):
    from app.engine import conversation_intelligence

    monkeypatch.setattr(conversation_intelligence.settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(conversation_intelligence.settings, "GOOGLE_API_KEY", "")

    insight = await conversation_intelligence.analyze_live_message(
        original_text="Pho 500k, pay now",
        translated_text="Pho 500k, pay now",
        source_lang="en",
        target_lang="vi",
        speaker="vendor",
        region="hanoi",
        recent_context=[],
    )

    assert insight.intent == "price_discussion"
    assert insight.price_vnd == 500000
    assert insight.risk_level in ("medium", "high")
    assert insight.confidence >= 0.5
    assert insight.should_promote_to_price_db is False
