import json
import statistics
import math
from loguru import logger
from app.core.config import settings

def crawl_delivery_price(item_name: str, region: str = "hanoi") -> int:
    """
    Use Gemini Search Grounding to scrape real-time prices for an item from delivery apps.
    Includes strict Anti-Hallucination Guardrails.
    Returns the median price if successful, or 0 if failed/rejected.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_key)
        
        # Try to initialize with search tools. Fallback to basic if SDK version differs.
        try:
            model = genai.GenerativeModel("gemini-2.0-flash", tools="google_search_retrieval")
        except Exception:
            model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = f"""Search the web for the current price of "{item_name}" in {region}, Vietnam on food delivery apps like ShopeeFood, Foody, or GrabFood.
You MUST find exactly 3 different prices from 3 different casual/street food vendors (not luxury restaurants).
For each, provide the URL of the vendor's page.

Return ONLY a valid JSON array in this exact format:
[
  {{"vendor": "Vendor Name 1", "price_vnd": 35000, "url": "https://shopeefood.vn/..."}},
  {{"vendor": "Vendor Name 2", "price_vnd": 40000, "url": "https://shopeefood.vn/..."}},
  {{"vendor": "Vendor Name 3", "price_vnd": 30000, "url": "https://shopeefood.vn/..."}}
]
Do not include any markdown, backticks, or extra text."""

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.1)
        )
        
        raw_text = response.text.strip().removeprefix('```json').removesuffix('```').strip()
        data = json.loads(raw_text)
        
        if not isinstance(data, list) or len(data) < 3:
            logger.warning(f"Crawler rejected: AI did not return 3 prices for {item_name}.")
            return 0
            
        prices = []
        for entry in data[:3]:
            price = entry.get("price_vnd", 0)
            url = entry.get("url", "")
            
            # Guardrail 1: Must have URL (Source verification)
            if not url.startswith("http"):
                logger.warning(f"Crawler rejected: Missing valid URL for {item_name}.")
                return 0
                
            # Guardrail 2: Hard Bounds Sanity Check
            if price < 10000 or price > 300000:
                logger.warning(f"Crawler rejected: Price {price} for {item_name} out of physical bounds [10k-300k].")
                return 0
                
            prices.append(price)
            
        # Guardrail 3: Statistical Outlier Rejection
        mean_price = statistics.mean(prices)
        std_dev = statistics.stdev(prices) if len(prices) > 1 else 0
        
        # If standard deviation is > 40% of the mean, the AI is likely confused between luxury and street food, or hallucinating.
        if std_dev > (0.4 * mean_price):
            logger.warning(f"Crawler rejected: Variance too high for {item_name}. Prices: {prices}")
            return 0
            
        # All guardrails passed, return the Median
        final_price = int(statistics.median(prices))
        logger.info(f"Crawler SUCCESS for {item_name}: Prices {prices} -> Median {final_price}")
        
        # Store in DB temporarily
        from app.data.price_db import add_ai_crawler_price
        add_ai_crawler_price(region, item_name, final_price, data[0].get("url", "ai_crawler"))
        
        return final_price

    except Exception as e:
        logger.error(f"Crawler failed for {item_name}: {e}")
        return 0
