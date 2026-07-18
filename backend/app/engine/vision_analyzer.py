"""
Tour-resQ AI Vision Analyzer
============================
Analyzes images of menus and receipts to detect physical anomalies,
layout forgery, and "double menus" (different prices for tourists vs locals).
"""
import json
from pydantic import BaseModel, Field
import google.generativeai as genai
from app.core.config import settings

class VisionAnalysisResult(BaseModel):
    forgery_detected: bool = Field(description="True if physical anomalies or price discrepancies are detected in the layout.")
    risk_level: str = Field(description="LOW, MEDIUM, HIGH")
    detected_items: list[str] = Field(description="List of distinct items extracted from the menu/receipt.")
    analysis_reason: str = Field(description="Detailed reason for the forgery detection. E.g. 'Stickers pasted over original prices' or 'English prices are significantly higher than Vietnamese prices on the same page.'")

async def analyze_menu_layout(image_base64: str, mime_type: str = "image/jpeg", lang: str = "en") -> VisionAnalysisResult:
    """
    In a real environment, this sends the image to Gemini Vision API.
    For this hackathon demo, we will simulate the behavior if API key is missing,
    or attempt to use the real API if a key is provided and an image is uploaded.
    """
    
    if not settings.gemini_key:
        return None

    # Real implementation
    try:
        genai.configure(api_key=settings.gemini_key)
        # Gemini 2.5 Flash supports both vision and structured outputs
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = """You are an expert fraud investigator in Vietnam specializing in tourist traps.
Analyze the provided image of a restaurant menu, receipt, or POS credit card terminal.

Do NOT just extract the text. Look deeply at the LAYOUT, PHYSICAL anomalies, and CONTEXTUAL TRAPS.
Specifically look for:
1. Double Menus: Are there separate price lists for English vs. Vietnamese? Is the English price significantly higher?
2. Physical Tampering: Are there stickers pasted over old prices? Does the font/ink look mismatched or manually altered?
3. Invisible Quantities (The /100g Trap): Look closely for tiny text like '/100g', '/lạng', '/kg' next to seemingly cheap prices.
4. Dual Currency (POS Trap): If it's a credit card terminal, check the currency symbol. Is it charging in USD ($) when the user expects VND?
5. Money-Exchange Trap (20k vs 500k): For images of Vietnamese currency, carefully distinguish the blue 500,000 VNĐ notes from the similarly-colored 20,000 VNĐ notes. Count them to ensure the tourist isn't being shortchanged.

Return a structured JSON assessment."""

        # Create the image dict format expected by the model
        image_part = {
            "mime_type": mime_type,
            "data": image_base64
        }
        
        response = model.generate_content(
            [prompt, image_part],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=VisionAnalysisResult,
                temperature=0.1
            )
        )
        
        if not response.text:
            return VisionAnalysisResult(
                forgery_detected=False,
                risk_level="LOW",
                detected_items=[],
                analysis_reason="No response from vision model."
            )
            
        data_dict = json.loads(response.text)
        return VisionAnalysisResult(**data_dict)

    except Exception as e:
        print(f"Vision API Error: {e}")
        return VisionAnalysisResult(
            forgery_detected=False,
            risk_level="LOW",
            detected_items=[],
            analysis_reason="Failed to analyze image."
        )
