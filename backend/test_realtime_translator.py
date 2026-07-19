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
@pytest.mark.parametrize("spoken_text", [
    "30 nghin dong mot chiec banh mi",
    "30 nghìn đồng một chiếc bánh mì",
])
@pytest.mark.parametrize(("target_lang", "expected_translation"), [
    ("en", "30,000 VND for one banh mi."),
    ("ko", "반미 하나에 30,000동입니다."),
    ("zh", "一个越南法棍是30,000越南盾。"),
    ("ru", "Один бань ми стоит 30 000 донгов."),
])
async def test_demo_banh_mi_phrasebook_returns_exact_translation_without_network(
    monkeypatch,
    spoken_text,
    target_lang,
    expected_translation,
):
    from app.engine import realtime_translator

    class FailingClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("network should not be used for demo phrasebook matches")

    monkeypatch.setattr(realtime_translator.settings, "TRANSLATION_PROVIDER", "mymemory")
    monkeypatch.setattr(realtime_translator.httpx, "AsyncClient", FailingClient)

    result = await realtime_translator.translate_realtime(
        text=spoken_text,
        source_lang="vi",
        target_lang=target_lang,
        context="casual",
    )

    assert result["translation"] == expected_translation
    assert result["provider"] == "demo_phrasebook"
    assert result["error"] == ""


@pytest.mark.anyio
@pytest.mark.parametrize(("text", "source_lang", "target_lang", "expected_translation"), [
    (
        "gia nay da la gia tot roi",
        "vi",
        "en",
        "This is already a good price.",
    ),
    (
        "duoc toi ban cho ban hai muoi nghin",
        "vi",
        "en",
        "Okay, I can sell it to you for 20,000 VND.",
    ),
    (
        "Can you sell it for twenty thousand dong?",
        "en",
        "vi",
        "Bạn có thể bán giá hai mươi nghìn đồng không?",
    ),
])
async def test_demo_negotiation_script_returns_exact_translation_without_network(
    monkeypatch,
    text,
    source_lang,
    target_lang,
    expected_translation,
):
    from app.engine import realtime_translator

    class FailingClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("network should not be used for demo phrasebook matches")

    monkeypatch.setattr(realtime_translator.settings, "TRANSLATION_PROVIDER", "mymemory")
    monkeypatch.setattr(realtime_translator.httpx, "AsyncClient", FailingClient)

    result = await realtime_translator.translate_realtime(
        text=text,
        source_lang=source_lang,
        target_lang=target_lang,
        context="negotiation",
    )

    assert result["translation"] == expected_translation
    assert result["provider"] == "demo_phrasebook"
    assert result["error"] == ""


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
