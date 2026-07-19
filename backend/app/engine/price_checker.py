"""
Tour-resQ Dynamic Pricing Engine
================================
Two-layer approach:
  Layer 1: Database-backed Z-score anomaly detection (offline, fast)
  Layer 2: Gemini LLM contextual analysis (online, nuanced)

Uses a 3-tier verdict system:
  - fair: z-score <= 1.0
  - slightly_high: 1.0 < z-score <= 2.0
  - overpriced: z-score > 2.0
  - insufficient_data: sample_count < MIN_SAMPLE_SIZE

Does not make binary "Scam" decisions, but rather provides nuanced Tiers.
"""
import json
import math
from typing import Optional, Tuple
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from app.core.config import settings
from app.data.price_db import get_price_stats

# ─────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────

class PriceEstimationData(BaseModel):
    """Structured output expected from Gemini"""
    item_name: str = Field(description="The core item being purchased, translated to English")
    quantity: float = Field(description="The number of items. If not specified, default to 1.0")
    total_asked_price_vnd: float = Field(description="The total price demanded in VND. Convert from 'k' (400k = 400000).")
    min_fair_unit_price_vnd: float = Field(description="The absolute lowest fair market price for ONE item in this specific hyper-local area.")
    max_fair_unit_price_vnd: float = Field(description="The highest acceptable fair market price for ONE item in this specific hyper-local area before it becomes a 'Tourist Premium'.")
    is_bespoke_art: bool = Field(description="True ONLY if the item is custom-made, fine art, handcrafted jewelry, or bespoke tailoring where price varies wildly by artisan skill. False for mass-produced food, transport, or standard goods.")
    typology_match: str = Field(description="If this matches a known scam pattern (e.g. 'Street Vendor Overcharge', 'Taxi Meter Jump'), output the name. Otherwise 'None'.")

class PriceAssessmentResult(BaseModel):
    item_name: str
    unit_price: float
    max_fair_price: float
    markup_percentage: float
    tier: str  # FAIR, PREMIUM, EXTREME_OVERCHARGE, BESPOKE_ART
    assessment_message: str
    typology_match: str

class PriceCheckResult(BaseModel):
    """Result from the DB-backed price check (Layer 1)."""
    item_name: str
    asked_price: float
    median_price: float
    mad: float
    z_score: float
    sample_count: int
    tier: str  # fair, slightly_high, overpriced, insufficient_data
    confidence: float  # 0.0 - 1.0
    price_range: str  # e.g. "35,000 - 65,000 VND"
    message: str
    source: str = "database"
    last_updated: str = ""


# ─────────────────────────────────────────────────────────
# LAYER 1: DATABASE-BACKED PRICE CHECK (offline, fast)
# ─────────────────────────────────────────────────────────

def check_single_price(
    item_name: str,
    asked_price: float,
    region: str = "hanoi",
    venue_type: str = "all",
) -> PriceCheckResult:
    """
    Check a single item price against the SQLite price database.
    Uses Z-score anomaly detection with configurable thresholds.
    
    Returns insufficient_data when sample_count < MIN_SAMPLE_SIZE.
    """
    stats = get_price_stats(region, item_name, venue_type)
    
    if stats is None:
        return PriceCheckResult(
            item_name=item_name,
            asked_price=asked_price,
            median_price=0,
            mad=0,
            z_score=0,
            sample_count=0,
            tier="insufficient_data",
            confidence=0.0,
            price_range="N/A",
            message=f"No price data found for '{item_name}' in {region}. Cannot verify.",
        )
    
    sample_count = stats["sample_count"]
    median_price = stats["median_price"]
    mad = stats["mad"]
    min_price = stats["min_price"]
    max_price = stats["max_price"]
    last_updated = stats.get("last_updated", "")
    
    # Refuse to conclude if insufficient data
    if sample_count < settings.MIN_SAMPLE_SIZE:
        # Fallback to AI Delivery Crawler for Real-time Web Data
        from app.engine.delivery_crawler import crawl_delivery_price
        crawled_price = crawl_delivery_price(item_name, region)
        
        if crawled_price > 0:
            # Successfully scraped and passed all Guardrails
            if asked_price <= crawled_price * 1.2:
                tier = "fair"
                msg_prefix = "Fair price."
            elif asked_price <= crawled_price * 1.5:
                tier = "slightly_high"
                msg_prefix = "Slightly high."
            else:
                tier = "overpriced"
                msg_prefix = "Overpriced!"
                
            return PriceCheckResult(
                item_name=item_name,
                asked_price=asked_price,
                median_price=crawled_price,
                mad=0.0,
                z_score=0.0,
                sample_count=1,
                tier=tier,
                confidence=0.85, # High confidence due to real-time verification
                price_range=f"{int(crawled_price*0.9):,} - {int(crawled_price*1.2):,} VND",
                message=f"Live Web Data: Found real-time average of {int(crawled_price):,} VND on Food Delivery Apps. {msg_prefix}",
                source="ai_crawler",
                last_updated="Just now",
            )
            
        return PriceCheckResult(
            item_name=item_name,
            asked_price=asked_price,
            median_price=median_price,
            mad=mad,
            z_score=0,
            sample_count=sample_count,
            tier="insufficient_data",
            confidence=sample_count / settings.MIN_SAMPLE_SIZE,
            price_range=f"{int(min_price):,} - {int(max_price):,} VND",
            message=f"Only {sample_count} price samples for '{item_name}' in {region}. "
                    f"Need at least {settings.MIN_SAMPLE_SIZE} to make a reliable verdict. "
                    f"Current range: {int(min_price):,} - {int(max_price):,} VND.",
            last_updated=last_updated,
        )
    
    # Calculate robust Z-score based on MAD
    # Z = (X - Median) / (1.4826 * MAD)
    # Using 1.4826 converts MAD to an estimator of standard deviation for a normal distribution
    robust_std_dev = 1.4826 * mad
    if robust_std_dev > 0:
        z_score = (asked_price - median_price) / robust_std_dev
    else:
        # All samples are identical or too concentrated — any deviation is significant
        z_score = 0.0 if asked_price == median_price else 3.0
    
    # Determine tier based on z-score thresholds from config
    if z_score <= settings.PRICE_TIER_GREEN:
        tier = "fair"
        message = (f"Fair price. {int(asked_price):,} VND is within the normal range "
                   f"for {item_name} in {region} (median: {int(median_price):,} VND).")
    elif z_score <= settings.PRICE_TIER_YELLOW:
        tier = "slightly_high"
        message = (f"Slightly above average. {int(asked_price):,} VND is higher than "
                   f"the typical {int(median_price):,} VND but may be normal for this venue type.")
    else:
        tier = "overpriced"
        message = (f"Significantly overpriced. {int(asked_price):,} VND is abnormally high "
                   f"compared to the typical {int(median_price):,} VND. "
                   f"Normal range: {int(min_price):,} - {int(max_price):,} VND.")
    
    # Confidence based on sample count (more data = higher confidence)
    confidence = min(1.0, sample_count / 20)  # 20+ samples = 100% confidence
    
    return PriceCheckResult(
        item_name=item_name,
        asked_price=asked_price,
        median_price=median_price,
        mad=mad,
        z_score=round(z_score, 2),
        sample_count=sample_count,
        tier=tier,
        confidence=round(confidence, 2),
        price_range=f"{int(min_price):,} - {int(max_price):,} VND",
        message=message,
        last_updated=last_updated,
    )

def calculate_tier_and_message(
    unit_price: float, 
    max_fair: float, 
    is_bespoke: bool, 
    lang: str = "en"
) -> Tuple[str, float, str]:
    """Calculates the markup percentage and assigns a nuanced tier."""
    
    if max_fair <= 0:
        return "UNKNOWN", 0.0, "Could not determine a fair baseline price."

    markup = ((unit_price - max_fair) / max_fair) * 100
    
    # Handle bespoke items first
    if is_bespoke:
        msg = "This is a bespoke, handmade, or artistic item. Pricing depends heavily on craftsmanship and material quality. Inspect carefully before negotiating."
        if lang == "vi":
            msg = "Đây là sản phẩm thủ công/đặc thù. Giá trị phụ thuộc vào độ tinh xảo và chất liệu. Hãy kiểm tra kỹ trước khi chốt giá."
        return "BESPOKE_ART", markup, msg

    # Calculate tiers based on markup
    if markup <= 20:
        msg = f"Fair price. This is within the normal market range for this area."
        if lang == "vi":
            msg = "Giá hợp lý. Mức giá này nằm trong mặt bằng chung tại khu vực này."
        return "FAIR", markup, msg
        
    elif markup <= 100:
        msg = f"Tourist Premium. You are paying a {(markup):.0f}% markup above average. You should negotiate down to around {int(max_fair):,} VND."
        if lang == "vi":
            msg = f"Giá khách du lịch. Bạn đang bị tính chênh {markup:.0f}%. Khuyên bạn nên mặc cả xuống khoảng {int(max_fair):,} VNĐ."
        return "PREMIUM", markup, msg
        
    else:
        msg = f"Severe Overcharge! This is a {(markup):.0f}% markup. The real price should be around {int(max_fair):,} VND. Strongly recommend refusing or walking away."
        if lang == "vi":
            msg = f"Dấu hiệu chém giá nghiêm trọng! Mức giá bị dội lên {markup:.0f}% (giá gốc chỉ khoảng {int(max_fair):,} VNĐ). Tuyệt đối không mua hoặc trả đúng giá."
        return "EXTREME_OVERCHARGE", markup, msg

async def analyze_price_context(
    description: str,
    location_context: str,
    lang: str = "en"
) -> Optional[PriceAssessmentResult]:
    """
    Advanced LLM query to extract entities and estimate local fair value.
    """
    if not settings.gemini_key:
        return None

    client = genai.Client(api_key=settings.gemini_key)

    prompt = f"""You are a hyper-local pricing expert in Vietnam.
Analyze the following tourist interaction: "{description}"
Context/Location: {location_context}

IMPORTANT SLANG DICTIONARY & CONTEXT RULES:
- "lít" = 100,000 VND, "củ" = 1,000,000 VND
- THREATS: If the interaction involves intimidation (e.g., "không đưa đủ không xong đâu"), set typology_match to "Intimidation / Slang Overcharge".
- ROUTE DEVIATION: If the user says the taxi is "đi ngược hướng" (going the wrong way) or "nhảy nhanh" (meter tampering), set typology_match to "KIDNAPPING_RISK". This is an extreme emergency.
- WEATHER SURGE: If the context mentions "mưa" (rain), "ngập" (flooding), or rush hour, increase the `max_fair_unit_price_vnd` by 80% to account for legitimate surge pricing. Do not flag as an overcharge if it's within this surge bracket.

Extract the item, quantity, and total demanded price.
Estimate the min and max FAIR market price for ONE UNIT of this item in this SPECIFIC location.
If it's a bespoke/handicraft item, set is_bespoke_art to true.
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PriceEstimationData,
                temperature=0.1
            )
        )
        
        if not response.text:
            return None
            
        data_dict = json.loads(response.text)
        data = PriceEstimationData(**data_dict)
        
        # Calculate derived metrics
        qty = data.quantity if data.quantity > 0 else 1.0
        unit_price = data.total_asked_price_vnd / qty
        
        tier, markup, msg = calculate_tier_and_message(
            unit_price=unit_price,
            max_fair=data.max_fair_unit_price_vnd,
            is_bespoke=data.is_bespoke_art,
            lang=lang
        )
        
        return PriceAssessmentResult(
            item_name=data.item_name,
            unit_price=unit_price,
            max_fair_price=data.max_fair_unit_price_vnd,
            markup_percentage=markup,
            tier=tier,
            assessment_message=msg,
            typology_match=data.typology_match
        )
        
    except Exception as e:
        print(f"Price Analysis Error: {e}")
        return None


# ─────────────────────────────────────────────────────────
# LAYER 3: OCR-TO-DB PIPELINE (Image → Items → Z-Score)
# ─────────────────────────────────────────────────────────

class OCRItem(BaseModel):
    """A single item extracted from a menu/receipt image."""
    item_name: str = Field(description="The item name in English (e.g. 'pho', 'beer', 'taxi ride')")
    item_name_vi: str = Field(description="The item name in Vietnamese if visible (e.g. 'phở', 'bia')")
    price_vnd: float = Field(description="The price in VND. Convert from 'k' notation (e.g. 45k = 45000).")
    quantity: float = Field(description="Quantity if specified, otherwise 1.0")
    unit: str = Field(description="Unit of measurement (e.g. 'item', '100g', 'kg', 'plate')")

class OCRExtractionResult(BaseModel):
    """Structured extraction from an image."""
    items: list[OCRItem] = Field(description="All items with prices found in the image")
    currency_detected: str = Field(description="The currency detected (VND, USD, etc.)")
    language_detected: str = Field(description="Primary language of the menu/receipt")

class OCRPriceCheckResult(BaseModel):
    """Complete result of OCR + price verification."""
    items_checked: list[dict]
    total_asked: float
    total_fair_estimate: float
    overall_verdict: str  # fair, slightly_high, overpriced, mixed, insufficient_data
    currency_warning: str  # Empty or warning about wrong currency
    summary: str
    requires_human_confirmation: bool = Field(default=False, description="True if OCR results need human verification to prevent false alarms")


async def check_price_from_image(
    image_base64: str,
    region: str = "hanoi",
    lang: str = "en",
) -> Optional[OCRPriceCheckResult]:
    """
    Full pipeline: Image → Gemini Vision OCR → Extract items → DB lookup → Z-score.
    
    This is the endpoint the evaluation document specifically requires.
    """
    if not settings.gemini_key:
        return None

    client = genai.Client(api_key=settings.gemini_key)

    prompt = """You are an expert fraud investigator and OCR specialist analyzing a Vietnamese restaurant menu, handwritten receipt, or price board.

Extract ALL purchased items with their prices. Your analysis must handle the following extreme cases:
1. HANDWRITTEN RECEIPTS: Carefully decipher messy handwriting, abbreviated Vietnamese names (e.g., 'mực nướng', 'cua rang me').
2. FOREIGN LANGUAGES: If the menu/receipt is written in Chinese, Korean, English, or Russian, translate the item names to English for the 'item_name' field, but KEEP the original text in the 'item_name_vi' field (e.g. if it says 炒飯, put 'Fried Rice' as item_name and '炒飯' as item_name_vi).
3. HIDDEN METRICS (The /100g trap): Look closely for tiny text like '/100g', '/lạng', '/kg' next to a seemingly cheap price.
4. PRICE FORMATTING (CRITICAL): In Vietnam, '30' or '30k' on a menu almost always means 30,000 VND. Also, Vietnamese uses a dot '.' as a thousands separator (e.g. 30.000 = 30,000). If a food/drink price is less than 1000 (e.g. '45'), you MUST multiply it by 1000 to get the full VND amount (45000) for the 'price_vnd' field.
5. QUANTITY MULTIPLIERS: For 'price_vnd', ALWAYS extract the TOTAL price for that line item on the receipt (e.g. if it says '3 x 50,000 = 150,000', price_vnd MUST be 150000, and quantity MUST be 3).
6. IGNORE TOTALS: DO NOT extract 'Total', 'Tổng cộng', 'Subtotal', 'Tax', or 'Thanh toán' rows as separate items. ONLY extract the actual goods/services.

Even if the receipt is extremely simple, blurry, or missing context, you MUST extract whatever items and prices you can see.
Return a structured JSON list of all items found."""

    try:
        import base64
        image_data = base64.b64decode(image_base64)
        image_part = types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
        
        # Build schema manually as a plain dictionary to avoid google-genai Pydantic bugs
        ocr_schema = {
            "type": "OBJECT",
            "properties": {
                "items": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "item_name": {"type": "STRING"},
                            "item_name_vi": {"type": "STRING"},
                            "price_vnd": {"type": "NUMBER"},
                            "quantity": {"type": "NUMBER"},
                            "unit": {"type": "STRING"},
                        },
                        "required": ["item_name", "price_vnd"]
                    }
                },
                "currency_detected": {"type": "STRING"},
                "language_detected": {"type": "STRING"}
            },
            "required": ["items"]
        }

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, image_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ocr_schema,
                temperature=0.1
            )
        )

        if not response.text:
            print("Response text is empty. Response object:", response)
            return None

        # Parse json safely handling missing optional fields
        import json
        data_dict = json.loads(response.text)
        
        items_checked = []
        total_asked = 0
        total_fair = 0
        worst_tier = "fair"
        tier_rank = {"fair": 0, "insufficient_data": 1, "slightly_high": 2, "overpriced": 3}

        from app.data.price_db import search_item
        
        raw_items = data_dict.get("items", [])
        for ocr_item in raw_items:
            item_name = ocr_item.get("item_name", "Unknown")
            item_name_vi = ocr_item.get("item_name_vi", "")
            price_vnd = float(ocr_item.get("price_vnd", 0.0))
            quantity = float(ocr_item.get("quantity", 1.0))
            unit = ocr_item.get("unit", "item")
            
            # Search DB for canonical item name to prevent false "insufficient_data"
            search_results = search_item(item_name_vi, region) if item_name_vi else []
            if not search_results:
                search_results = search_item(item_name, region)
                
            if search_results:
                lookup_name = search_results[0]["item_name"]
            else:
                lookup_name = item_name.lower().replace(" ", "_")
                
            unit_price = price_vnd / max(quantity, 1.0)

            # If unit is per-weight, flag it
            per_weight_warning = ""
            if unit in ("100g", "kg", "lạng"):
                per_weight_warning = f"Price is per {unit}! Actual cost depends on weight."

            db_check = check_single_price(lookup_name, unit_price, region)

            item_result = {
                "item_name": item_name,
                "item_name_vi": item_name_vi,
                "asked_price": price_vnd,
                "unit_price": unit_price,
                "quantity": quantity,
                "unit": unit,
                "per_weight_warning": per_weight_warning,
                "db_tier": db_check.tier,
                "db_median_price": db_check.median_price,
                "db_z_score": db_check.z_score,
                "db_sample_count": db_check.sample_count,
                "db_message": db_check.message,
            }
            items_checked.append(item_result)

            total_asked += price_vnd
            if db_check.median_price > 0:
                total_fair += db_check.median_price * max(quantity, 1.0)

            if tier_rank.get(db_check.tier, 0) > tier_rank.get(worst_tier, 0):
                worst_tier = db_check.tier

        # Currency warning
        currency_warning = ""
        currency_detected = data_dict.get("currency_detected", "VND")
        if currency_detected != "VND":
            currency_warning = (f"WARNING: Prices appear to be in {currency_detected}, "
                              f"not VND! This could be a dual-currency trap.")

        # Summary
        n_items = len(items_checked)
        n_overpriced = sum(1 for i in items_checked if i["db_tier"] == "overpriced")
        n_slightly_high = sum(1 for i in items_checked if i["db_tier"] == "slightly_high")
        n_insufficient = sum(1 for i in items_checked if i["db_tier"] == "insufficient_data")

        if n_overpriced > 0:
            summary = f"{n_overpriced} of {n_items} items are overpriced. Total asked: {int(total_asked):,} VND."
        elif n_slightly_high > 0:
            summary = f"{n_slightly_high} of {n_items} items are slightly high. Total asked: {int(total_asked):,} VND."
        elif n_insufficient == n_items:
            summary = f"Cannot verify any of the {n_items} items — insufficient price data in our database."
        elif n_insufficient > 0:
            summary = f"{n_items - n_insufficient} of {n_items} items were verified; {n_insufficient} need more local price data. Total asked: {int(total_asked):,} VND."
        else:
            summary = f"All {n_items} items appear fairly priced. Total: {int(total_asked):,} VND."

        if total_fair > 0:
            summary += f" Estimated fair total: {int(total_fair):,} VND."
        if currency_warning:
            summary = currency_warning + " " + summary

        # Determine overall verdict
        if n_overpriced > 0 and n_overpriced < n_items:
            overall = "mixed"
        else:
            overall = worst_tier

        # Human-in-the-loop: Require confirmation if any item is overpriced, 
        # or if there's a currency warning, to prevent false alarms from OCR errors
        requires_human_confirmation = (n_overpriced > 0) or bool(currency_warning) or (n_insufficient > 0)

        return OCRPriceCheckResult(
            items_checked=items_checked,
            total_asked=total_asked,
            total_fair_estimate=total_fair,
            overall_verdict=overall,
            currency_warning=currency_warning,
            summary=summary,
            requires_human_confirmation=requires_human_confirmation,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"OCR Price Check Error: {e}")
        return OCRPriceCheckResult(
            items_checked=[],
            total_asked=0,
            total_fair_estimate=0,
            overall_verdict="error",
            currency_warning="",
            summary=f"API Error: {str(e)}",
            requires_human_confirmation=True
        )
