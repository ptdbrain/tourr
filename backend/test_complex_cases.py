import asyncio
from app.engine.price_checker import analyze_price_context

async def test():
    print("Testing Case 1: 5 donuts for 400k at Hoan Kiem")
    res1 = await analyze_price_context(
        description="I just bought 5 donuts on walking street and the lady asked for 400k VND",
        location_context="Hoan Kiem Walking Street, Hanoi",
        lang="vi"
    )
    if res1:
        print(f"Tier: {res1.tier}, Item: {res1.item_name}, Unit Price: {res1.unit_price}, Max Fair: {res1.max_fair_price}, Markup: {res1.markup_percentage:.1f}%")
        print(f"Message: {res1.assessment_message}")
    
    print("\nTesting Case 2: Hoi An Silk Suit for 3 million")
    res2 = await analyze_price_context(
        description="Tailor wants 3 million VND for a custom silk suit",
        location_context="Hoi An Old Town",
        lang="vi"
    )
    if res2:
        print(f"Tier: {res2.tier}, Item: {res2.item_name}, Bespoke? {res2.tier == 'BESPOKE_ART'}")
        print(f"Message: {res2.assessment_message}")

if __name__ == "__main__":
    asyncio.run(test())
