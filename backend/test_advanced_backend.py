import asyncio
import os
import json
from dotenv import load_dotenv

# Load env variables for Gemini API Key
load_dotenv()

from app.engine.price_checker import analyze_price_context
from app.engine.defense_scripts import generate_defense_script

async def test_scenarios():
    print("==================================================")
    print("TOUR-RESQ: ADVANCED BACKEND RAG & PRICING TEST")
    print("==================================================\n")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not found in environment.")
        return

    # ─────────────────────────────────────────────────────────
    # TEST CASE 1: The Classic "Donut Extortion"
    # ─────────────────────────────────────────────────────────
    print("▶ TEST CASE 1: The 'Donut Extortion' Scam")
    desc_1 = "A street vendor put 5 donuts in a bag for me and now she is demanding 400,000 VND. I didn't even ask for them."
    loc_1 = "Hanoi Walking Street (Hoan Kiem Lake)"
    
    print(f"Context: {loc_1}")
    print(f"User Input: {desc_1}")
    print("Analyzing...")
    
    res_1 = await analyze_price_context(desc_1, loc_1, lang="en")
    if res_1:
        print("\n--- ANALYSIS RESULT ---")
        print(f"Item extracted: {res_1.item_name}")
        print(f"Calculated Unit Price: {int(res_1.unit_price):,} VND")
        print(f"AI Estimated Max Fair Price: {int(res_1.max_fair_price):,} VND")
        print(f"Markup Percentage: +{res_1.markup_percentage:.0f}%")
        print(f"Typology Match: {res_1.typology_match}")
        print(f"TIER: {res_1.tier}")
        print(f"Assessment: {res_1.assessment_message}")
        
        script_1 = generate_defense_script(
            tier=res_1.tier, 
            typology=res_1.typology_match, 
            fair_price=res_1.max_fair_price * 5, # total fair price for script
            asked_price=400000, 
            item_name=res_1.item_name
        )
        print(f"\n[ACTIVE DEFENSE AUDIO SCRIPT (Vietnamese)]:\n=> '{script_1}'")
    else:
        print("Analysis failed.")

    print("\n" + "="*50 + "\n")

    # ─────────────────────────────────────────────────────────
    # TEST CASE 2: The "Hoi An Bespoke Silk Suit"
    # ─────────────────────────────────────────────────────────
    print("▶ TEST CASE 2: Specialty Goods (Bespoke Suit)")
    desc_2 = "I am getting a custom-tailored 3-piece suit made of 100% Vietnamese silk. They quoted me 3,500,000 VND total."
    loc_2 = "Hoi An Ancient Town"
    
    print(f"Context: {loc_2}")
    print(f"User Input: {desc_2}")
    print("Analyzing...")
    
    res_2 = await analyze_price_context(desc_2, loc_2, lang="en")
    if res_2:
        print("\n--- ANALYSIS RESULT ---")
        print(f"Item extracted: {res_2.item_name}")
        print(f"Calculated Unit Price: {int(res_2.unit_price):,} VND")
        print(f"TIER: {res_2.tier}")
        print(f"Assessment: {res_2.assessment_message}")
    else:
        print("Analysis failed.")
        
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(test_scenarios())
