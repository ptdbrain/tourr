# Realtime Translation And AI Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a low-latency live translation pipeline that translates speech quickly, then analyzes each utterance with AI in parallel and stores safe structured observations for future price/scam intelligence.

**Architecture:** Keep translation on the fast path and AI analysis off the blocking path. `/api/v1/live/message` must return translated text quickly using Google Translate when configured, while a background task extracts intent, prices, scam signals, and stores observations in a separate table instead of writing directly to the trusted price database. The frontend speaks the translated text immediately, then shows AI warnings or captured-price notices when analysis results arrive.

**Tech Stack:** FastAPI, SQLite, existing `httpx`, existing `google-genai`, browser SpeechRecognition, browser SpeechSynthesis, vanilla JavaScript.

## Global Constraints

- Do not block live speech translation on Gemini analysis.
- Do not write AI-extracted prices directly into `price_references`.
- Store AI-extracted data first as unverified observations.
- Use Google Translate REST API through existing `httpx`; do not add a new dependency unless REST cannot satisfy the use case.
- Keep Gemini available for analysis and fallback translation.
- Preserve the existing frontend API shape as much as possible.
- Treat `vi`, `en`, `ko`, `zh`, and `ru` as supported live languages.
- Scrub PII before AI analysis and before database storage.
- If external translation fails, return the original text with an explicit provider error rather than crashing the live flow.

---

## File Structure

- Modify `backend/app/core/config.py`
  - Add `GOOGLE_TRANSLATE_API_KEY`, `TRANSLATION_PROVIDER`, `ENABLE_LIVE_AI_ANALYSIS`, and `LIVE_ANALYSIS_MIN_CONFIDENCE`.
- Create `backend/app/engine/realtime_translator.py`
  - Owns Google Translate fast path and Gemini fallback interface.
- Create `backend/app/engine/conversation_intelligence.py`
  - Owns Gemini structured analysis of live utterances.
- Modify `backend/app/data/price_db.py`
  - Add `conversation_observations` table and functions to insert/list observations.
- Modify `backend/app/api/live_negotiation.py`
  - Return fast translation immediately and queue analysis/storage in a background task.
  - Add endpoint to fetch recent insights for a live session.
- Modify `frontend/app.js`
  - Speak translation immediately.
  - Poll or refresh insights shortly after each translated message.
  - Render AI risk and price extraction notices without delaying translation.
- Create `backend/test_realtime_translator.py`
  - Tests provider routing, Google success, Google failure fallback shape.
- Create `backend/test_conversation_observations.py`
  - Tests schema creation and safe observation insertion.
- Create `backend/test_live_negotiation_realtime.py`
  - Tests live endpoint returns translation without waiting for analysis.
- Modify `README.md`
  - Document new environment variables and the fast-path/AI-path design.

---

### Task 1: Add Runtime Configuration

**Files:**
- Modify: `backend/app/core/config.py`
- Test: `backend/test_realtime_translator.py`

**Interfaces:**
- Consumes: environment variables.
- Produces:
  - `settings.GOOGLE_TRANSLATE_API_KEY: str`
  - `settings.TRANSLATION_PROVIDER: str`
  - `settings.ENABLE_LIVE_AI_ANALYSIS: bool`
  - `settings.LIVE_ANALYSIS_MIN_CONFIDENCE: float`

- [ ] **Step 1: Write the failing config test**

Create `backend/test_realtime_translator.py` with:

```python
import os
from app.core.config import Settings


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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest test_realtime_translator.py::test_live_translation_settings_are_available -v
```

Expected: FAIL because the settings do not exist yet.

- [ ] **Step 3: Add settings**

Modify `backend/app/core/config.py` inside `Settings`:

```python
    # --- Live Translation ---
    GOOGLE_TRANSLATE_API_KEY: str = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")
    TRANSLATION_PROVIDER: str = os.getenv("TRANSLATION_PROVIDER", "gemini").lower()
    ENABLE_LIVE_AI_ANALYSIS: bool = os.getenv("ENABLE_LIVE_AI_ANALYSIS", "true").lower() == "true"
    LIVE_ANALYSIS_MIN_CONFIDENCE: float = float(os.getenv("LIVE_ANALYSIS_MIN_CONFIDENCE", "0.65"))
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd backend
python -m pytest test_realtime_translator.py::test_live_translation_settings_are_available -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/core/config.py backend/test_realtime_translator.py
git commit -m "feat: add live translation settings"
```

---

### Task 2: Create Fast Translation Provider

**Files:**
- Create: `backend/app/engine/realtime_translator.py`
- Modify: `backend/test_realtime_translator.py`

**Interfaces:**
- Consumes:
  - `settings.TRANSLATION_PROVIDER`
  - `settings.GOOGLE_TRANSLATE_API_KEY`
  - existing `backend/app/engine/translator.py::translate_text`
- Produces:
  - `async def translate_realtime(text: str, source_lang: str, target_lang: str, context: str = "casual") -> dict`
  - Return dict keys: `translation`, `provider`, `latency_ms`, `romanization`, `cultural_note`, `error`

- [ ] **Step 1: Add tests for provider behavior**

Append to `backend/test_realtime_translator.py`:

```python
import pytest


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest test_realtime_translator.py -v
```

Expected: FAIL because `app.engine.realtime_translator` does not exist.

- [ ] **Step 3: Implement `realtime_translator.py`**

Create `backend/app/engine/realtime_translator.py`:

```python
import html
import time
import httpx

from app.core.config import settings
from app.engine.translator import translate_text as translate_with_gemini


GOOGLE_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"

GOOGLE_LANG_MAP = {
    "en": "en",
    "vi": "vi",
    "ko": "ko",
    "zh": "zh-CN",
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

        gemini_result = await translate_with_gemini(text, source_lang, target_lang, context)
        gemini_result.setdefault("romanization", "")
        gemini_result.setdefault("cultural_note", "")
        gemini_result["provider"] = "gemini_fallback"
        gemini_result["latency_ms"] = round((time.perf_counter() - started_at) * 1000)
        gemini_result["error"] = google_result["error"]
        return gemini_result

    gemini_result = await translate_with_gemini(text, source_lang, target_lang, context)
    gemini_result.setdefault("translation", text)
    gemini_result.setdefault("romanization", "")
    gemini_result.setdefault("cultural_note", "")
    gemini_result["provider"] = "gemini"
    gemini_result["latency_ms"] = round((time.perf_counter() - started_at) * 1000)
    gemini_result.setdefault("error", "")
    return gemini_result
```

- [ ] **Step 4: Run tests**

Run:

```powershell
cd backend
python -m pytest test_realtime_translator.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/engine/realtime_translator.py backend/test_realtime_translator.py
git commit -m "feat: add realtime translation provider"
```

---

### Task 3: Add Safe Conversation Observation Storage

**Files:**
- Modify: `backend/app/data/price_db.py`
- Create: `backend/test_conversation_observations.py`

**Interfaces:**
- Consumes: existing `get_db()` and `init_price_db()`.
- Produces:
  - `def add_conversation_observation(...args...) -> int`
  - `def get_recent_session_observations(session_id: str, limit: int = 10) -> list[dict]`

- [ ] **Step 1: Write observation DB tests**

Create `backend/test_conversation_observations.py`:

```python
from app.data.price_db import (
    init_price_db,
    add_conversation_observation,
    get_recent_session_observations,
)


def test_add_and_list_conversation_observation():
    init_price_db()

    observation_id = add_conversation_observation(
        session_id="session-1",
        message_id="message-1",
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

    rows = get_recent_session_observations("session-1", limit=5)

    assert observation_id > 0
    assert len(rows) >= 1
    assert rows[0]["message_id"] == "message-1"
    assert rows[0]["item_name"] == "pho"
    assert rows[0]["price_vnd"] == 500000
    assert rows[0]["should_promote_to_price_db"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest test_conversation_observations.py -v
```

Expected: FAIL because functions do not exist.

- [ ] **Step 3: Add table in `init_price_db()`**

In `backend/app/data/price_db.py`, inside the `cursor.executescript("""...""")` block, add:

```sql
        CREATE TABLE IF NOT EXISTS conversation_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message_id TEXT NOT NULL UNIQUE,
            region TEXT NOT NULL,
            speaker TEXT NOT NULL,
            source_lang TEXT NOT NULL,
            target_lang TEXT NOT NULL,
            original_text_scrubbed TEXT DEFAULT '',
            translated_text TEXT DEFAULT '',
            intent TEXT DEFAULT 'unknown',
            item_name TEXT DEFAULT '',
            item_name_vi TEXT DEFAULT '',
            price_vnd INTEGER DEFAULT 0,
            quantity REAL DEFAULT 1.0,
            risk_level TEXT DEFAULT 'none',
            scam_type TEXT DEFAULT '',
            confidence REAL DEFAULT 0.0,
            should_alert BOOLEAN DEFAULT 0,
            should_promote_to_price_db BOOLEAN DEFAULT 0,
            is_verified BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_conversation_observations_session
            ON conversation_observations(session_id, created_at);

        CREATE INDEX IF NOT EXISTS idx_conversation_observations_item_region
            ON conversation_observations(region, item_name, price_vnd);
```

- [ ] **Step 4: Add insert/list functions**

Append to `backend/app/data/price_db.py`:

```python
def add_conversation_observation(
    session_id: str,
    message_id: str,
    region: str,
    speaker: str,
    source_lang: str,
    target_lang: str,
    original_text_scrubbed: str,
    translated_text: str,
    intent: str,
    item_name: str,
    item_name_vi: str,
    price_vnd: int,
    quantity: float,
    risk_level: str,
    scam_type: str,
    confidence: float,
    should_alert: bool,
    should_promote_to_price_db: bool,
) -> int:
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO conversation_observations
            (session_id, message_id, region, speaker, source_lang, target_lang,
             original_text_scrubbed, translated_text, intent, item_name, item_name_vi,
             price_vnd, quantity, risk_level, scam_type, confidence,
             should_alert, should_promote_to_price_db)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        message_id,
        region,
        speaker,
        source_lang,
        target_lang,
        original_text_scrubbed,
        translated_text,
        intent,
        item_name,
        item_name_vi,
        price_vnd,
        quantity,
        risk_level,
        scam_type,
        confidence,
        1 if should_alert else 0,
        1 if should_promote_to_price_db else 0,
    ))

    conn.commit()
    observation_id = cursor.lastrowid
    conn.close()
    return int(observation_id)


def get_recent_session_observations(session_id: str, limit: int = 10) -> list[dict]:
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT * FROM conversation_observations
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (session_id, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]
```

- [ ] **Step 5: Run test**

Run:

```powershell
cd backend
python -m pytest test_conversation_observations.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/data/price_db.py backend/test_conversation_observations.py
git commit -m "feat: store live conversation observations"
```

---

### Task 4: Build Structured AI Conversation Analysis

**Files:**
- Create: `backend/app/engine/conversation_intelligence.py`
- Modify: `backend/test_conversation_observations.py`

**Interfaces:**
- Consumes:
  - `settings.gemini_key`
  - `settings.LIVE_ANALYSIS_MIN_CONFIDENCE`
- Produces:
  - `class LiveMessageInsight(BaseModel)`
  - `async def analyze_live_message(original_text: str, translated_text: str, source_lang: str, target_lang: str, speaker: str, region: str, recent_context: list[dict]) -> LiveMessageInsight`

- [ ] **Step 1: Add deterministic fallback tests**

Append to `backend/test_conversation_observations.py`:

```python
import pytest


@pytest.mark.asyncio
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest test_conversation_observations.py::test_analyze_live_message_without_gemini_uses_safe_fallback -v
```

Expected: FAIL because `conversation_intelligence.py` does not exist.

- [ ] **Step 3: Implement `conversation_intelligence.py`**

Create `backend/app/engine/conversation_intelligence.py`:

```python
import json
import re
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from app.core.config import settings


class LiveMessageInsight(BaseModel):
    intent: str = Field(default="unknown")
    item_name: str = Field(default="")
    item_name_vi: str = Field(default="")
    price_vnd: int = Field(default=0)
    quantity: float = Field(default=1.0)
    risk_level: str = Field(default="none")
    scam_type: str = Field(default="")
    confidence: float = Field(default=0.0)
    should_alert: bool = Field(default=False)
    should_promote_to_price_db: bool = Field(default=False)
    summary: str = Field(default="")


def _extract_price_vnd(text: str) -> int:
    normalized = text.lower().replace(",", "").replace(".", "")
    match_k = re.search(r"(\d+(?:\.\d+)?)\s*k\b", normalized)
    if match_k:
        return int(float(match_k.group(1)) * 1000)

    match_vnd = re.search(r"(\d{4,})\s*(vnd|dong|đồng|₫)?", normalized)
    if match_vnd:
        return int(match_vnd.group(1))

    return 0


def _fallback_insight(original_text: str, translated_text: str) -> LiveMessageInsight:
    combined = f"{original_text} {translated_text}".lower()
    price_vnd = _extract_price_vnd(combined)
    is_price = price_vnd > 0 or any(word in combined for word in ["price", "cost", "bao nhiêu", "giá", "tiền"])
    is_suspicious = any(word in combined for word in ["scam", "fake", "police", "ép", "lừa", "too expensive", "overcharge"])

    if is_suspicious:
        risk_level = "high"
    elif price_vnd >= 300000:
        risk_level = "medium"
    else:
        risk_level = "none"

    return LiveMessageInsight(
        intent="price_discussion" if is_price else "conversation",
        price_vnd=price_vnd,
        risk_level=risk_level,
        scam_type="possible_overcharge" if price_vnd >= 300000 else "",
        confidence=0.55 if is_price else 0.3,
        should_alert=is_suspicious or price_vnd >= 300000,
        should_promote_to_price_db=False,
        summary="Potential price discussion detected." if is_price else "",
    )


async def analyze_live_message(
    original_text: str,
    translated_text: str,
    source_lang: str,
    target_lang: str,
    speaker: str,
    region: str,
    recent_context: list[dict],
) -> LiveMessageInsight:
    if not settings.gemini_key:
        return _fallback_insight(original_text, translated_text)

    context_text = "\n".join(
        f"{row.get('speaker', 'unknown')}: {row.get('original_text', '')} -> {row.get('translated_text', '')}"
        for row in recent_context[-5:]
    )

    prompt = f"""Analyze one live tourist-vendor utterance in Vietnam.

Recent context:
{context_text}

Current utterance:
speaker: {speaker}
source_lang: {source_lang}
target_lang: {target_lang}
region: {region}
original_text: {original_text}
translated_text: {translated_text}

Rules:
1. Extract a price only if it is explicitly spoken.
2. Convert 500k to 500000 VND.
3. Do not mark suspicious or overcharge prices as fair market prices.
4. should_promote_to_price_db must be true only when the phrase clearly describes a normal paid price, not a complaint, threat, or scam.
5. Keep item_name in simple English, item_name_vi in Vietnamese if clear.

Return JSON only."""

    try:
        client = genai.Client(api_key=settings.gemini_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LiveMessageInsight,
                temperature=0.1,
            ),
        )
        if not response.text:
            return _fallback_insight(original_text, translated_text)

        insight = LiveMessageInsight(**json.loads(response.text))
        if insight.confidence < settings.LIVE_ANALYSIS_MIN_CONFIDENCE:
            insight.should_promote_to_price_db = False
        if insight.risk_level in ("medium", "high"):
            insight.should_promote_to_price_db = False
        return insight
    except Exception:
        return _fallback_insight(original_text, translated_text)
```

- [ ] **Step 4: Run fallback test**

Run:

```powershell
cd backend
python -m pytest test_conversation_observations.py::test_analyze_live_message_without_gemini_uses_safe_fallback -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/engine/conversation_intelligence.py backend/test_conversation_observations.py
git commit -m "feat: analyze live speech into structured insights"
```

---

### Task 5: Wire Fast Translation And Background Analysis Into Live API

**Files:**
- Modify: `backend/app/api/live_negotiation.py`
- Create: `backend/test_live_negotiation_realtime.py`

**Interfaces:**
- Consumes:
  - `translate_realtime(...)`
  - `analyze_live_message(...)`
  - `add_conversation_observation(...)`
  - `get_recent_session_observations(...)`
- Produces:
  - `POST /api/v1/live/message` returns translated text immediately.
  - `GET /api/v1/live/insights/{session_id}` returns stored recent observations.

- [ ] **Step 1: Write live endpoint tests**

Create `backend/test_live_negotiation_realtime.py`:

```python
from fastapi.testclient import TestClient

from main import app
from app.api import live_negotiation


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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest test_live_negotiation_realtime.py -v
```

Expected: FAIL because `region`, `translate_realtime`, and `analysis_status` are not wired.

- [ ] **Step 3: Modify request model**

In `backend/app/api/live_negotiation.py`, update imports:

```python
from app.engine.realtime_translator import translate_realtime
from app.engine.conversation_intelligence import analyze_live_message
from app.data.price_db import add_conversation_observation, get_recent_session_observations
```

Then update `LiveMessageRequest`:

```python
class LiveMessageRequest(BaseModel):
    session_id: str
    text: str
    source_lang: str
    target_lang: str
    speaker: str
    region: str = "hanoi"
```

- [ ] **Step 4: Add background analysis function**

Add above `process_live_message`:

```python
async def analyze_and_store_message(
    session_id: str,
    message_id: str,
    original_text: str,
    translated_text: str,
    source_lang: str,
    target_lang: str,
    speaker: str,
    region: str,
    recent_context: list[dict],
) -> None:
    insight = await analyze_live_message(
        original_text=original_text,
        translated_text=translated_text,
        source_lang=source_lang,
        target_lang=target_lang,
        speaker=speaker,
        region=region,
        recent_context=recent_context,
    )

    add_conversation_observation(
        session_id=session_id,
        message_id=message_id,
        region=region,
        speaker=speaker,
        source_lang=source_lang,
        target_lang=target_lang,
        original_text_scrubbed=original_text,
        translated_text=translated_text,
        intent=insight.intent,
        item_name=insight.item_name,
        item_name_vi=insight.item_name_vi,
        price_vnd=insight.price_vnd,
        quantity=insight.quantity,
        risk_level=insight.risk_level,
        scam_type=insight.scam_type,
        confidence=insight.confidence,
        should_alert=insight.should_alert,
        should_promote_to_price_db=insight.should_promote_to_price_db,
    )
```

- [ ] **Step 5: Update live message endpoint**

Change signature:

```python
@router.post("/api/v1/live/message")
async def process_live_message(req: LiveMessageRequest, bg_tasks: BackgroundTasks):
```

Replace the translation block with:

```python
    message_id = str(uuid.uuid4())
    translation_result = await translate_realtime(
        text=safe_text,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
        context=context,
    )

    translated_text = translation_result.get("translation", "")
```

After appending to `active_sessions`, queue analysis:

```python
    if settings.ENABLE_LIVE_AI_ANALYSIS:
        bg_tasks.add_task(
            analyze_and_store_message,
            session_id=req.session_id,
            message_id=message_id,
            original_text=safe_text,
            translated_text=translated_text,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
            speaker=req.speaker,
            region=req.region,
            recent_context=active_sessions[req.session_id][-5:],
        )
        analysis_status = "queued"
    else:
        analysis_status = "disabled"
```

Update response:

```python
    return {
        "status": "success",
        "message_id": message_id,
        "original": safe_text,
        "translated": translated_text,
        "romanization": translation_result.get("romanization", ""),
        "provider": translation_result.get("provider", ""),
        "translation_latency_ms": translation_result.get("latency_ms", 0),
        "translation_error": translation_result.get("error", ""),
        "analysis_status": analysis_status,
        "is_price_discussion": is_price_discussion,
        "is_suspicious": is_suspicious,
    }
```

- [ ] **Step 6: Add insights endpoint**

Add below `process_live_message`:

```python
@router.get("/api/v1/live/insights/{session_id}")
async def get_live_insights(session_id: str, limit: int = 5):
    observations = get_recent_session_observations(session_id, limit=limit)
    return {
        "status": "success",
        "session_id": session_id,
        "observations": observations,
    }
```

- [ ] **Step 7: Run tests**

Run:

```powershell
cd backend
python -m pytest test_live_negotiation_realtime.py test_realtime_translator.py test_conversation_observations.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add backend/app/api/live_negotiation.py backend/test_live_negotiation_realtime.py
git commit -m "feat: split live translation from AI analysis"
```

---

### Task 6: Stop Unsafe Direct Ambient Price Writes

**Files:**
- Modify: `backend/app/api/live_negotiation.py`
- Modify: `backend/app/data/price_db.py`
- Test: `backend/test_conversation_observations.py`

**Interfaces:**
- Consumes: `conversation_observations`.
- Produces: no automatic writes from AI-extracted live speech into `price_references`.

- [ ] **Step 1: Add safety test**

Append to `backend/test_conversation_observations.py`:

```python
def test_suspicious_observation_is_not_promoted_to_price_reference():
    init_price_db()

    observation_id = add_conversation_observation(
        session_id="session-scam",
        message_id="message-scam",
        region="hanoi",
        speaker="tourist",
        source_lang="en",
        target_lang="vi",
        original_text_scrubbed="He is asking 500k for pho, this is a scam",
        translated_text="Anh ấy đòi 500k cho phở, đây là lừa đảo",
        intent="scam_report",
        item_name="pho",
        item_name_vi="phở",
        price_vnd=500000,
        quantity=1.0,
        risk_level="high",
        scam_type="overcharge",
        confidence=0.95,
        should_alert=True,
        should_promote_to_price_db=False,
    )

    rows = get_recent_session_observations("session-scam", limit=1)

    assert observation_id > 0
    assert rows[0]["should_promote_to_price_db"] == 0
    assert rows[0]["is_verified"] == 0
```

- [ ] **Step 2: Remove automatic telemetry promotion**

In `backend/app/api/live_negotiation.py`, delete or stop calling:

```python
from app.data.price_db import add_ambient_price
```

Do not call `process_ambient_telemetry` from `conclude_live_session`. Keep final verdict analysis if useful, but remove the line:

```python
bg_tasks.add_task(process_ambient_telemetry, transcript, req.region)
```

- [ ] **Step 3: Keep `add_ambient_price` only for explicitly verified future use**

Leave `add_ambient_price` in `backend/app/data/price_db.py`, but do not call it from live speech. This preserves compatibility while preventing unsafe DB poisoning.

- [ ] **Step 4: Run tests**

Run:

```powershell
cd backend
python -m pytest test_conversation_observations.py test_live_negotiation_realtime.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/api/live_negotiation.py backend/test_conversation_observations.py
git commit -m "fix: prevent unverified live speech price promotion"
```

---

### Task 7: Update Frontend For Fast Translation Plus Delayed AI Insights

**Files:**
- Modify: `frontend/app.js`

**Interfaces:**
- Consumes:
  - `POST /api/v1/live/message`
  - `GET /api/v1/live/insights/{session_id}`
- Produces:
  - Immediate translated text and speech.
  - AI insight toast shown after background analysis completes.

- [ ] **Step 1: Add region to live message payload**

In `frontend/app.js`, inside `handleMessage`, change request body to:

```javascript
body: JSON.stringify({
    session_id: liveSessionId,
    text,
    source_lang: src,
    target_lang: tgt,
    speaker,
    region: getRegionFromCoordinates(userLocation.lat, userLocation.lng)
})
```

- [ ] **Step 2: Speak translation immediately**

Keep the current block:

```javascript
if (data.translated) {
    document.getElementById(tgtEl).textContent = data.translated;
    if (window.speechSynthesis) {
        const utterance = new SpeechSynthesisUtterance(data.translated);
        utterance.lang = tgt === 'vi' ? 'vi-VN' : tgt === 'ko' ? 'ko-KR' : tgt === 'zh' ? 'zh-CN' : 'en-US';
        window.speechSynthesis.speak(utterance);
    }
}
```

Do not wait for insights before speaking.

- [ ] **Step 3: Add insight refresh function**

Add below `handleMessage`:

```javascript
async function refreshLiveInsights(sessionId) {
    if (!sessionId) return;
    try {
        const res = await fetch(API_BASE + `/api/v1/live/insights/${sessionId}?limit=3`);
        const data = await res.json();
        if (data.status !== 'success' || !data.observations?.length) return;

        const latest = data.observations[0];
        if (latest.should_alert) {
            showSmartWidget("WARNING", latest.summary || "Potential tourist risk detected.", true);
        } else if (latest.price_vnd > 0) {
            const item = latest.item_name || "item";
            showSmartWidget("PRICE CAPTURED", `${item}: ${latest.price_vnd.toLocaleString()} VND`, false);
        }
    } catch(e) {}
}
```

- [ ] **Step 4: Schedule insight refresh after each message**

At the end of successful `handleMessage`, add:

```javascript
if (data.analysis_status === 'queued') {
    setTimeout(() => refreshLiveInsights(liveSessionId), 900);
    setTimeout(() => refreshLiveInsights(liveSessionId), 1800);
}
```

- [ ] **Step 5: Improve fallback UI when translation provider fails**

Inside `handleMessage`, after `const data = await res.json();`, add:

```javascript
if (data.translation_error) {
    showSmartWidget("TRANSLATION FALLBACK", "Primary translation provider failed. Fallback output shown.", false);
}
```

- [ ] **Step 6: Run frontend syntax check**

Run:

```powershell
node --check frontend\app.js
```

Expected: no output and exit code 0.

- [ ] **Step 7: Commit**

```powershell
git add frontend/app.js
git commit -m "feat: show live AI insights after fast translation"
```

---

### Task 8: Add Manual Smoke Test Script

**Files:**
- Create: `backend/test_live_manual.py`

**Interfaces:**
- Consumes: running backend app and configured environment.
- Produces: simple manual command to verify live translation endpoint without the browser.

- [ ] **Step 1: Create manual smoke script**

Create `backend/test_live_manual.py`:

```python
import asyncio
import httpx


BASE_URL = "http://127.0.0.1:8000"


async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        start = await client.post(f"{BASE_URL}/api/v1/live/start")
        start.raise_for_status()
        session_id = start.json()["session_id"]

        msg = await client.post(f"{BASE_URL}/api/v1/live/message", json={
            "session_id": session_id,
            "text": "Cai nay bao nhieu tien?",
            "source_lang": "vi",
            "target_lang": "en",
            "speaker": "vendor",
            "region": "hanoi",
        })
        msg.raise_for_status()
        print("LIVE MESSAGE:", msg.json())

        await asyncio.sleep(2)
        insights = await client.get(f"{BASE_URL}/api/v1/live/insights/{session_id}")
        insights.raise_for_status()
        print("INSIGHTS:", insights.json())


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run with backend**

Terminal 1:

```powershell
cd backend
python main.py
```

Terminal 2:

```powershell
cd backend
python test_live_manual.py
```

Expected:

```text
LIVE MESSAGE: {'status': 'success', ... 'translated': 'How much is this?', ...}
INSIGHTS: {'status': 'success', 'session_id': '...', 'observations': [...]}
```

- [ ] **Step 3: Commit**

```powershell
git add backend/test_live_manual.py
git commit -m "test: add live translation smoke script"
```

---

### Task 9: Document Environment And Operating Model

**Files:**
- Modify: `README.md`
- Create or modify: `backend/.env.example`

**Interfaces:**
- Consumes: settings from Task 1.
- Produces: clear setup instructions for Google Translate plus Gemini analysis.

- [ ] **Step 1: Add `.env.example`**

Create `backend/.env.example` if missing:

```env
GEMINI_API_KEY=
GOOGLE_TRANSLATE_API_KEY=
TRANSLATION_PROVIDER=google
ENABLE_LIVE_AI_ANALYSIS=true
LIVE_ANALYSIS_MIN_CONFIDENCE=0.65
SOS_WEBHOOK_URL=
```

- [ ] **Step 2: Add README section**

Add to `README.md`:

```markdown
## Live Translation Architecture

Tour-resQ uses a two-path live translation design:

1. Fast path: browser SpeechRecognition converts speech to text, backend translates with Google Translate API when `TRANSLATION_PROVIDER=google`, frontend reads the translated text with SpeechSynthesis.
2. AI path: Gemini analyzes the same utterance in the background, extracts prices, risk signals, and intent, then stores unverified observations in `conversation_observations`.

This keeps conversation latency low while preserving AI safety. AI-extracted prices are not inserted directly into the trusted price reference database.

### Environment Variables

```env
GOOGLE_TRANSLATE_API_KEY=your_google_translate_key
TRANSLATION_PROVIDER=google
GEMINI_API_KEY=your_gemini_key
ENABLE_LIVE_AI_ANALYSIS=true
LIVE_ANALYSIS_MIN_CONFIDENCE=0.65
```
```

- [ ] **Step 3: Commit**

```powershell
git add README.md backend/.env.example
git commit -m "docs: document live translation architecture"
```

---

### Task 10: Final Verification

**Files:**
- No new files.

**Interfaces:**
- Consumes: all previous tasks.
- Produces: verified end-to-end behavior.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
cd backend
python -m pytest test_realtime_translator.py test_conversation_observations.py test_live_negotiation_realtime.py -v
```

Expected: PASS.

- [ ] **Step 2: Run existing backend smoke tests**

Run:

```powershell
cd backend
python test_quick.py
```

Expected: prints `ALL TESTS PASSED!`.

- [ ] **Step 3: Run frontend syntax check**

Run:

```powershell
node --check frontend\app.js
```

Expected: no output and exit code 0.

- [ ] **Step 4: Run manual live flow**

Run backend:

```powershell
cd backend
python main.py
```

Then run:

```powershell
cd backend
python test_live_manual.py
```

Expected:

```text
LIVE MESSAGE:
```

contains translated text and provider metadata.

```text
INSIGHTS:
```

contains observations or an empty list if Gemini is disabled. If Gemini key is configured, at least one observation should appear for price discussion text.

- [ ] **Step 5: Browser verification**

Open:

```text
http://127.0.0.1:8000/app/index.html
```

Manual checks:

- Select English.
- Start journey.
- Open Local Chat.
- Tap vendor mic.
- Say: `Cái này bao nhiêu tiền?`
- Confirm translated English appears quickly.
- Confirm translated text is spoken.
- Wait 1 to 2 seconds.
- Confirm smart widget shows either price discussion or warning insight.

- [ ] **Step 6: Commit verification notes**

If all checks pass, add a short note to `ai_collaboration_log.md`:

```markdown
## Live Translation Upgrade

- Added fast Google Translate provider for live conversation.
- Kept Gemini analysis on a background path.
- Stored AI-extracted prices as unverified observations, not trusted price references.
- Verified backend tests, JS syntax, and manual live smoke test.
```

Commit:

```powershell
git add ai_collaboration_log.md
git commit -m "docs: record live translation verification"
```

---

## Self-Review

**Spec coverage:** The plan covers realtime translation, AI analysis after translation, optional AI normalization through structured analysis, observation storage, frontend delayed insight display, and safeguards against polluting the trusted price database.

**Latency:** Translation is fast path. Gemini analysis is background task plus insight polling.

**Safety:** AI-extracted suspicious prices are stored in `conversation_observations`; they are not promoted to `price_references`.

**Feasibility:** No new frontend framework. No new backend dependency required for Google Translate because `httpx` already exists.

**Main risk:** Google Translate API requires a valid Google Cloud API key and billing. Without the key, the system falls back to Gemini or returns original text with an error field.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-18-realtime-translation-ai-analysis.md`. Two execution options:

1. Subagent-Driven (recommended): dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution: execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
