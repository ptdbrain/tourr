# AI Collaboration Log - Tour-resQ
**Team**: Brandflow  
**Hackathon**: Vietnam AI Innovation Challenge (VAIC) 2026

## 1. Overview of AI Usage
Throughout the 48-hour hackathon, our team leveraged Generative AI to accelerate development, improve code quality, and implement the core intelligence of the Tour-resQ platform. We did not use AI merely to write boilerplate; we collaborated with AI as a pair programmer and technical architect.

## 2. Tools Used
- **Google Gemini 2.0 Flash/Pro**: Used via API for core features (OCR, scam detection, context translation).
- **DeepMind Agentic Assistant (Antigravity)**: Used as an autonomous pair-programmer to refactor code, implement robust statistics (Median/MAD), and fix bugs.
- **GitHub Copilot**: Inline code completions and documentation generation.

## 3. Key Collaboration Phases

### Phase 1: Ideation & Architecture Design
**Prompt Excerpt:**
> "We are building an app to protect tourists in Vietnam from scams. We want to use Edge AI and Gemini. Propose a system architecture that minimizes latency and protects user privacy."

**AI Contribution:** 
The AI suggested the hybrid architecture: Client-side Edge compression (Canvas EXIF stripping) -> Fast API Gateway -> SQLite local lookup for speed -> Gemini Vision for OCR only. This ensured we didn't send PII to the cloud.

### Phase 2: Building the Robust Pricing Engine
**Prompt Excerpt:**
> "The current pricing engine uses Mean and Standard Deviation, but it's failing when a vendor inputs an extreme outlier like 1 million VND for a coffee. How can we fix this?"

**AI Contribution:**
The AI pair-programmer recommended using **Median and Median Absolute Deviation (MAD)** instead. It autonomously dropped the old SQLite schema, rewrote the `rebuild_price_stats` function to compute MAD, and created a `test_metrics.py` script to prove 0% False Positives and 100% Recall.

### Phase 3: Prompt Engineering for Gemini Vision
**Prompt Excerpt:**
> "Write a prompt for Gemini Vision to extract items from a Vietnamese receipt and return a strict JSON schema with item_name, quantity, and price_vnd."

**AI Contribution:**
The AI provided the exact structured output schema used in `vision_analyzer.py`, including edge cases like converting 'k' (e.g., '40k') to '40000'.

## 4. Conclusion
AI was instrumental not just in coding, but in **Mathematical Modeling** (Median/MAD for anomaly detection) and **Security** (suggesting Rate Limiting and strict CORS). This allowed our team to focus on the UX and product vision, resulting in a production-ready MVP in just 48 hours.
