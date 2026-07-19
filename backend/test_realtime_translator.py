import pytest

from app.core.config import Settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_live_translation_settings_are_available(monkeypatch):
    monkeypatch.setenv("GOOGLE_TRANSLATE_API_KEY", "test-google-key")
    monkeypatch.setenv("TRANSLATION_PROVIDER", "google")
    monkeypatch.setenv("ENABLE_LIVE_AI_ANALYSIS", "true")
    monkeypatch.setenv("LIVE_ANALYSIS_MIN_CONFIDENCE", "0.72")

    settings = Settings()

    assert settings.GOOGLE_TRANSLATE_API_KEY == "test-google-key"
    assert settings.TRANSLATION_PROVIDER == "google"
    assert settings.ENABLE_LIVE_AI_ANALYSIS is True
    assert settings.LIVE_ANALYSIS_MIN_CONFIDENCE == 0.72


@pytest.mark.anyio
async def test_google_translate_success(monkeypatch):
    from app.engine import realtime_translator

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": {
                    "translations": [
                        {"translatedText": "How much is this?"}
                    ]
                }
            }

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, params, json):
            assert "translation.googleapis.com" in url
            assert params["key"] == "test-google-key"
            assert json["q"] == "Cai nay bao nhieu tien?"
            assert json["source"] == "vi"
            assert json["target"] == "en"
            return FakeResponse()

    monkeypatch.setattr(realtime_translator.settings, "GOOGLE_TRANSLATE_API_KEY", "test-google-key")
    monkeypatch.setattr(realtime_translator.settings, "TRANSLATION_PROVIDER", "google")
    monkeypatch.setattr(realtime_translator.httpx, "AsyncClient", FakeClient)

    result = await realtime_translator.translate_realtime(
        text="Cai nay bao nhieu tien?",
        source_lang="vi",
        target_lang="en",
        context="negotiation",
    )

    assert result["translation"] == "How much is this?"
    assert result["provider"] == "google"
    assert result["error"] == ""
    assert result["latency_ms"] >= 0


@pytest.mark.anyio
async def test_google_translate_missing_key_returns_error(monkeypatch):
    from app.engine import realtime_translator

    monkeypatch.setattr(realtime_translator.settings, "GOOGLE_TRANSLATE_API_KEY", "")
    monkeypatch.setattr(realtime_translator.settings, "TRANSLATION_PROVIDER", "google")

    result = await realtime_translator.translate_realtime(
        text="Xin chao",
        source_lang="vi",
        target_lang="en",
        context="casual",
    )

    assert result["translation"] == "Xin chao"
    assert result["provider"] == "google"
    assert result["error"] == "GOOGLE_TRANSLATE_API_KEY is not configured"


@pytest.mark.anyio
async def test_mymemory_translate_success(monkeypatch):
    from app.engine import realtime_translator

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "responseStatus": 200,
                "responseData": {
                    "translatedText": "Cai nay gia bao nhieu?"
                },
            }

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, params):
            assert "api.mymemory.translated.net/get" in url
            assert params["q"] == "How much is this?"
            assert params["langpair"] == "en|vi"
            assert params["mt"] == "1"
            return FakeResponse()

    monkeypatch.setattr(realtime_translator.settings, "TRANSLATION_PROVIDER", "mymemory")
    monkeypatch.setattr(realtime_translator.httpx, "AsyncClient", FakeClient)

    result = await realtime_translator.translate_realtime(
        text="How much is this?",
        source_lang="en",
        target_lang="vi",
        context="negotiation",
    )

    assert result["translation"] == "Cai nay gia bao nhieu?"
    assert result["provider"] == "mymemory"
    assert result["error"] == ""


@pytest.mark.anyio
async def test_mymemory_translate_error_keeps_original_text(monkeypatch):
    from app.engine import realtime_translator

    class FakeResponse:
        status_code = 429

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "responseStatus": 429,
                "responseDetails": "quota finished",
                "responseData": {
                    "translatedText": ""
                },
            }

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, params):
            return FakeResponse()

    monkeypatch.setattr(realtime_translator.settings, "TRANSLATION_PROVIDER", "mymemory")
    monkeypatch.setattr(realtime_translator.httpx, "AsyncClient", FakeClient)

    result = await realtime_translator.translate_realtime(
        text="How much is this?",
        source_lang="en",
        target_lang="vi",
        context="negotiation",
    )

    assert result["translation"] == "How much is this?"
    assert result["provider"] == "mymemory"
    assert result["error"] == "quota finished"
