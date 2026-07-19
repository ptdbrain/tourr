# Tour-resQ — AI-Powered Tourist Protection Assistant

> *Your safety companion in Vietnam* | 베트남에서의 안전 도우미 | 您在越南的安全伙伴 | Ваш помощник безопасности во Вьетнаме

[![VAIC 2026](https://img.shields.io/badge/VAIC-2026-blue?style=flat-square)](https://vaic.vn)
[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-purple?style=flat-square&logo=google)](https://ai.google.dev)

## 📌 VAIC 2026 Deliverables
- **Live Deployed URL:** [https://touresq.vercel.app](https://touresq.vercel.app)
- **Backend API:** [https://tour-resq-production.up.railway.app](https://tour-resq-production.up.railway.app/health)
- **GitHub Repository:** [https://github.com/dinhmanhcvp/Tour-resQ](https://github.com/dinhmanhcvp/Tour-resQ)
- **AI Collaboration Log:** [ai_collaboration_log.md](./ai_collaboration_log.md)

## 🏆 How Tour-resQ Meets VAIC 2026 Criteria

| Criterion | Tour-resQ Implementation |
|-----------|--------------------------|
| **1. Technical Implementation (20 pts)** | Full-stack: Vanilla JS frontend (Vercel) + FastAPI backend (Railway) + SQLite. Robust Statistics (Median/MAD) for anomaly detection. CI/CD via GitHub auto-deploy. |
| **2. AI-Native Architecture (20 pts)** | AI is the core, not an add-on. **Agentic pipeline**: Gemini 2.5 Flash Vision OCR → Statistical Z-Score engine → LLM contextual translation. Dual-layer scam detection (keyword + AI reasoning). |
| **3. Business Viability (20 pts)** | Addresses $3.5B tourism protection gap. Crowdsourced price data grows with each user. Pilot-ready for Hanoi, scalable to 6+ cities. |
| **4. AI-Native UX (15 pts)** | "Panic-Mode" mobile-first UI. Slide-to-SOS. Flag-based language selection (no text barriers). Camera-first scanning. Show-to-vendor confrontation mode. |
| **5. AI Safety & Grounding (15 pts)** | **Privacy-minimized cloud inference**: Canvas compresses & strips EXIF on-device. No user accounts. No PII stored. AI grounded by statistical Z-Score (never hallucinated pricing). `requires_human_confirmation` flag for low-confidence results. |
| **6. Presentation & Defensibility (10 pts)** | Tested on real Vietnamese receipts (handwritten, abbreviated). Z-Score algorithm mathematically prevents false positives. |

## Problem

International tourists in Vietnam face **information asymmetry** that leads to:
- **Overcharging** — no way to verify if a price is fair
- **Taxi meter tampering** — rigged meters and long routes
- **Ghost tours** — fake tour operators taking deposits
- **Money exchange scams** — unfair rates and counterfeit bills

**No AI tool currently protects tourists in real time.** Tour-resQ changes that.

## Target Users

| Persona | Description | Key Need |
|---------|-------------|----------|
| 🇰🇷 Korean Solo Traveler | 20-35 years old, budget trips to Da Nang/Hoi An | Real-time price verification at restaurants |
| 🇨🇳 Chinese Tour Group | Group tours with language barrier | Emergency translation during disputes |
| 🇬🇧 English Backpacker | Long-stay, street food explorer | Scam pattern detection (taxi, tour) |
| 🇷🇺 Russian Resort Tourist | Nha Trang/Phu Quoc beach resorts | SOS hotline access with translation |

## Features

### 1. Instant Price Check (OCR → Z-Score → Verdict)
Photograph a receipt, menu, or price board → AI extracts items via Gemini 2.5 Flash Vision → compares against a **self-updating regional price database** (6 cities, 100+ items) → returns a **3-tier verdict** with statistical grounding:

| Tier | Meaning | Z-Score |
|------|---------|---------|
| ✅ Fair | Within normal range | <= 1.0 sigma |
| ⚠️ Slightly High | Above average, may be normal for venue type | 1.0-2.0 sigma |
| 🚨 Overpriced | Significantly above regional average | > 2.0 sigma |

### 2. Scam Detection (Dual-Layer)
Describe a suspicious situation (voice or text, in **any of the 4 supported languages**) → the system runs **dual-layer analysis**:
- **Layer 1**: Fast multilingual keyword matching across KO/ZH/EN/RU/VI (works offline)
- **Layer 2**: Gemini AI contextual analysis with Vietnam-specific actionable advice

### 3. SOS Emergency Dispatch
Slide-to-SOS gesture → auto-captures GPS → packages incident context → dispatches to control center → provides immediate hotline info with **localized phone numbers**.

### 4. Domain-Adapted Translation
Context-aware translation for **confrontation scenarios** (price disputes, scams). Includes:
- **Offline Phrasebook** — pre-translated phrases to show vendors
- **Voice Input** — Web Speech API in KO/ZH/EN/RU
- **Show-to-Vendor Mode** — large Vietnamese text for showing your phone

## Live Translation Architecture

Tour-resQ uses a two-path live translation design:

1. **Fast path:** browser SpeechRecognition converts speech to text, the backend translates with MyMemory public translation when `TRANSLATION_PROVIDER=mymemory` (no API key required for demo), and the frontend reads the translated text with SpeechSynthesis. Google Translate can still be enabled later with `TRANSLATION_PROVIDER=google`.
2. **AI path:** Gemini analyzes the same utterance in the background, extracts prices, risk signals, and intent, then stores editable unverified observations in `conversation_observations`.

This keeps conversation latency low while preserving AI safety. AI-extracted prices are not inserted directly into the trusted price reference database.

Editable observation data is exposed through `GET /api/v1/live/insights/{session_id}`, `PATCH /api/v1/live/observations/{observation_id}`, and `POST /api/v1/live/observations/{observation_id}/verify` so sample data can be reviewed and corrected before promotion.

### Live Translation Environment

```env
TRANSLATION_PROVIDER=mymemory
MYMEMORY_EMAIL=
GOOGLE_TRANSLATE_API_KEY=your_google_translate_key
GEMINI_API_KEY=your_gemini_key
ENABLE_LIVE_AI_ANALYSIS=true
LIVE_ANALYSIS_MIN_CONFIDENCE=0.65
```

## Supported Languages

| Code | Language | Market Priority |
|------|----------|----------------|
| EN | English | Primary |
| KO | 한국어 (Korean) | Priority |
| ZH | 中文 (Chinese) | Priority |
| RU | Русский (Russian) | Priority |

Language selection uses **flags, not text** — eliminating language barriers from the first interaction.

## Architecture

```
┌─────────────────────────────────────┐
│          Frontend (Mobile-First)     │
│  HTML/CSS/JS · Voice · Camera · GPS  │
│  Vercel Edge Network (Global CDN)    │
└─────────────┬───────────────────────┘
              │ REST API (HTTPS)
┌─────────────▼───────────────────────┐
│          FastAPI Backend (Railway)    │
├──────────────────────────────────────┤
│  i18n System (70+ keys × 4 lang)     │
├──────────────────────────────────────┤
│  Price Check Engine                  │
│  ├─ Gemini 2.5 Flash Vision OCR      │
│  ├─ SQLite Price DB (self-updating)  │
│  └─ Z-Score Anomaly Detection (MAD)  │
├──────────────────────────────────────┤
│  Scam Detector                       │
│  ├─ Multilingual Keyword Matching    │
│  └─ Gemini AI Contextual Analysis    │
├──────────────────────────────────────┤
│  Domain-Adapted Translator           │
│  ├─ Offline Phrasebook               │
│  └─ Gemini Translation + Cultural    │
├──────────────────────────────────────┤
│  SOS Dispatcher                      │
│  ├─ GPS + Photo + Context            │
│  └─ Webhook → Google Sheets         │
└──────────────────────────────────────┘
```

## Data Strategy: Crowdsourced Price Intelligence

> **The core innovation**: Reference-price data is undigitized. Tour-resQ solves this with a **community-driven flywheel**.

1. **Seed Data**: 101 items × 6 regions bootstrapped from local surveys
2. **"I PAID THIS" Button**: After each fair-price verification, tourists contribute their actual price
3. **Anti-Poisoning**: Contributions are only accepted when the price falls within the "fair" Z-Score range
4. **Continuous Learning**: Each contribution strengthens Median/MAD statistics, improving accuracy over time

## Quick Start

### Prerequisites
- Python 3.12+
- Gemini API key ([get one free](https://aistudio.google.com/apikey))

### Setup
```bash
git clone https://github.com/dinhmanhcvp/Tour-resQ.git
cd tour-resq/backend
pip install -r requirements.txt
cp .env.example .env  # Edit and add GEMINI_API_KEY
python main.py
```

### Access
- **Frontend**: http://localhost:8000/app/index.html
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/analyze-situation` | Combined price + scam analysis from text |
| `POST` | `/api/v1/check-price` | DB-backed price check with Z-score |
| `POST` | `/api/v1/check-price-ocr` | Full OCR pipeline: photo → item extraction → DB check |
| `POST` | `/api/v1/analyze-vision` | Vision AI for menu/receipt forgery detection |
| `POST` | `/api/v1/contribute-price` | Submit verified fair price (anti-poisoning) |
| `POST` | `/api/v1/translate` | Domain-adapted translation |
| `POST` | `/api/v1/translate/confrontation` | Show-to-vendor translation |
| `GET`  | `/api/v1/phrasebook` | Offline phrasebook |
| `POST` | `/api/v1/sos` | Emergency SOS dispatch with GPS |
| `GET`  | `/api/v1/emergency-info` | Hotline numbers (works offline) |
| `POST` | `/api/v1/dispatch-report` | Send report to nearest authority |
| `GET`  | `/api/v1/heatmap/data` | Crowdsourced scam heatmap data |

## AI Safety & Trust

- **3-tier verdicts** with statistical grounding (sample count, z-score, confidence)
- **Never accuses** — uses phrases like "this price is higher than the regional average"
- **False positive mitigation** — requires 2+ keyword matches for scam detection
- **Confidence threshold** — says "insufficient data" when sample size < 5
- **Self-updating** — fair prices automatically strengthen the database
- **Privacy-minimized cloud inference** — no user accounts, no persistent tracking; images compressed & EXIF-stripped on-device before upload; GPS used only for region resolution, not stored server-side

## Pilot Roadmap

| Phase | Timeline | Scope | Metrics |
|-------|----------|-------|---------|
| **Phase 1: MVP** | Month 1-2 | Hanoi Old Quarter (100 restaurants) | Price accuracy >90%, <5% false positive |
| **Phase 2: Expand** | Month 3-6 | 6 cities (Hanoi, HCMC, Da Nang, Hoi An, Nha Trang, Phu Quoc) | 10K+ monthly active users |
| **Phase 3: Scale** | Month 6-12 | Nationwide + App stores (iOS/Android PWA) | Partnership with Vietnam Tourism Board |

## Limitations & Future Work

- **OCR Accuracy**: Handwritten Vietnamese receipts can be challenging; ongoing prompt tuning improves results
- **Price Data Coverage**: Currently bootstrapped with 101 items; grows with user contributions
- **Scam Patterns**: AI analysis depends on user description quality; voice input helps
- **Privacy**: Currently privacy-minimized cloud inference (Gemini API); future work includes on-device models for fully offline operation
- **Language Coverage**: Web Speech API quality varies by browser/OS for Korean and Russian

## VAIC 2026

This project was built for the **Vietnam AI Challenge 2026** hackathon, addressing the challenge of protecting international tourists from common scams and overcharging in Vietnam.

**Team**: Brandflow

---

*Built with passion for a safer Vietnam travel experience*
