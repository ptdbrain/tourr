import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.parametrize(("description", "pattern_id", "severity", "expected"), [
    (
        "Taxi driver says the meter is broken and wants 800k to the airport",
        "taxi_meter",
        "high",
        "This resembles a taxi meter or route scam.",
    ),
    (
        "A shoe shiner grabbed my shoes and demands 500k",
        "forced_service",
        "high",
        "This resembles a forced shoe-shine service scam.",
    ),
    (
        "Money exchange shop offers only 500k VND for 50 dollars",
        "money_exchange",
        "high",
        "Severe exchange-rate scam: 50 USD for only 500,000 VND is far below a normal exchange value.",
    ),
])
async def test_guardian_demo_scenarios_are_deterministic(description, pattern_id, severity, expected):
    from app.engine.scam_detector import detect_scam_with_ai

    result = await detect_scam_with_ai(description, lang="en", region="hanoi")

    assert result.detected is True
    assert result.severity == severity
    assert result.patterns[0]["id"] == pattern_id
    assert result.ai_analysis == expected
    assert result.advice


def test_guardian_api_returns_demo_scam_assessments(monkeypatch):
    from app.api import routes

    async def fake_analyze_price_context(**kwargs):
        return None

    monkeypatch.setattr(routes, "analyze_price_context", fake_analyze_price_context)

    client = TestClient(app)
    for description, pattern_id in [
        ("Taxi driver says the meter is broken and wants 800k to the airport", "taxi_meter"),
        ("A shoe shiner grabbed my shoes and demands 500k", "forced_service"),
        ("Money exchange shop offers only 500k VND for 50 dollars", "money_exchange"),
    ]:
        response = client.post("/api/v1/analyze-situation", json={
            "description": description,
            "location": "hanoi",
            "language": "en",
            "lat": 21.0285,
            "lng": 105.8542,
        })

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["scam_assessment"]["detected"] is True
        assert body["scam_assessment"]["severity"] == "high"
        assert body["scam_assessment"]["patterns"][0]["id"] == pattern_id
        assert body["scam_assessment"]["ai_analysis"]
        if pattern_id == "money_exchange":
            assert "50 USD" in body["scam_assessment"]["ai_analysis"]
            assert "500,000 VND" in body["scam_assessment"]["ai_analysis"]
            assert "Do not hand over your cash" in body["scam_assessment"]["advice"][0]
