# 🛡️ Tour-resQ — AI-Powered Tourist Protection Assistant

> *Your safety companion in Vietnam* | 베트남에서의 안전 도우미 | 您在越南的安全伙伴 | Ваш помощник безопасности во Вьетнаме

[![VAIC 2026](https://img.shields.io/badge/VAIC-2026-blue?style=flat-square)](https://vaic.vn)
[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.0_Flash-purple?style=flat-square&logo=google)](https://ai.google.dev)

## 🎯 Problem

International tourists in Vietnam face **information asymmetry** that leads to:
- 💰 **Overcharging** — no way to verify if a price is fair
- 🚕 **Taxi meter tampering** — rigged meters and long routes
- 👻 **Ghost tours** — fake tour operators taking deposits
- 💱 **Money exchange scams** — unfair rates and counterfeit bills

**No AI tool currently protects tourists in real time.** Tour-resQ changes that.

## ✨ Features

### 1. 📷 Instant Price Check
Photograph a receipt, menu, or price board → AI extracts items via OCR → compares against a **self-updating regional price database** (6 cities, 100+ items) → returns a **3-tier verdict** with statistical grounding:

| Tier | Meaning | Z-Score |
|------|---------|---------|
| 🟢 Fair | Within normal range | ≤ 1.0 σ |
| 🟡 Slightly High | Above average, may be normal for venue type | 1.0–2.0 σ |
| 🔴 Overpriced | Significantly above regional average | > 2.0 σ |

### 2. 🔍 Scam Detection
Describe a suspicious situation (voice or text, in **any of the 4 supported languages**) → the system runs **dual-layer analysis**:
- **Layer 1**: Fast keyword matching across KO/ZH/EN/RU/VI (works offline)
- **Layer 2**: Gemini AI contextual analysis with Vietnam-specific advice

### 3. 🚨 SOS Emergency Dispatch
One tap (or **shake phone 3x**) → auto-captures GPS → packages incident context → dispatches to control center via webhook → provides immediate hotline info with **localized phone numbers**.

### 4. 💬 Domain-Adapted Translation
Not generic Google Translate — context-aware translation for **confrontation scenarios** (price disputes, scams). Includes:
- 📖 **Offline Phrasebook** — pre-translated phrases to show vendors
- 🗣️ **Voice Input** — Web Speech API in KO/ZH/EN/RU
- 📱 **Show-to-Vendor Mode** — large Vietnamese text for showing your phone

## 🌍 Supported Languages

| Flag | Language | Market Priority |
|------|----------|----------------|
| 🇬🇧 | English | Primary |
| 🇰🇷 | 한국어 (Korean) | Priority |
| 🇨🇳 | 中文 (Chinese) | Priority |
| 🇷🇺 | Русский (Russian) | Priority |

Language selection uses **flags, not text** — eliminating language barriers from the first interaction.

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│          Frontend (Mobile-First)     │
│  HTML/CSS/JS · Voice · Camera · GPS  │
└─────────────┬───────────────────────┘
              │ REST API
┌─────────────▼───────────────────────┐
│          FastAPI Backend             │
├──────────────────────────────────────┤
│  🌐 i18n System (70+ keys × 4 lang) │
├──────────────────────────────────────┤
│  📷 Price Check Engine               │
│  ├─ Gemini Vision OCR                │
│  ├─ SQLite Price DB (self-updating)  │
│  └─ Z-Score Anomaly Detection        │
├──────────────────────────────────────┤
│  🔍 Scam Detector                    │
│  ├─ Multilingual Keyword Matching    │
│  └─ Gemini AI Contextual Analysis    │
├──────────────────────────────────────┤
│  💬 Domain-Adapted Translator        │
│  ├─ Offline Phrasebook               │
│  └─ Gemini Translation + Cultural    │
├──────────────────────────────────────┤
│  🚨 SOS Dispatcher                   │
│  ├─ GPS + Photo + Context            │
│  └─ Webhook → Google Sheets          │
└──────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Gemini API key ([get one free](https://aistudio.google.com/apikey))

### Setup
```bash
# Clone
git clone https://github.com/your-team/tour-resq.git
cd tour-resq/backend

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run
python main.py
```

### Access
- **Frontend**: http://localhost:8000/app/index.html
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📁 Project Structure

```
tour-resq/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── api/routes.py          # All REST endpoints
│   │   ├── core/config.py         # Settings & environment
│   │   ├── i18n/translations.py   # 70+ keys × 4 languages
│   │   ├── data/
│   │   │   ├── price_db.py        # SQLite price database
│   │   │   └── seed_prices.json   # 101 bootstrap prices
│   │   └── engine/
│   │       ├── price_checker.py   # 3-tier anomaly detection
│   │       ├── scam_detector.py   # Dual-layer detection
│   │       ├── translator.py      # Domain-adapted translation
│   │       └── sos_dispatcher.py  # Emergency dispatch
│   └── test_quick.py              # Quick validation tests
├── frontend/
│   ├── index.html                 # Mobile-first SPA
│   ├── styles.css                 # Dark mode, premium UX
│   └── app.js                     # Camera, voice, GPS, haptics
└── README.md
```

## 🔑 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/check-price` | Check prices (manual input) |
| `POST` | `/api/check-price-ocr` | Check prices (photo upload) |
| `POST` | `/api/detect-scam` | Detect scam patterns |
| `POST` | `/api/translate` | Domain-adapted translation |
| `POST` | `/api/translate/confrontation` | Show-to-vendor translation |
| `GET` | `/api/phrasebook` | Offline phrasebook |
| `POST` | `/api/sos` | Emergency SOS dispatch |
| `GET` | `/api/emergency-info` | Hotline numbers |
| `GET` | `/api/languages` | Supported languages |
| `GET` | `/api/translations` | Batch UI translations |
| `GET` | `/api/onboarding` | Contextual tips for new arrivals |

## 🛡️ AI Safety & Trust

- **3-tier verdicts** with statistical grounding (sample count, z-score, confidence)
- **Never accuses** — uses phrases like "this price is higher than the regional average"
- **False positive mitigation** — requires 2+ keyword matches for scam detection
- **Confidence threshold** — says "insufficient data" when sample size < 5
- **Self-updating** — fair prices automatically strengthen the database
- **Privacy-first** — no user accounts, no persistent tracking, GPS only on SOS

## 🏆 VAIC 2026

This project was built for the **Vietnam AI Challenge 2026** hackathon, addressing the challenge of protecting international tourists from common scams and overcharging in Vietnam.

**Team**: Tour-resQ

---

*Built with ❤️ for a safer Vietnam travel experience*
