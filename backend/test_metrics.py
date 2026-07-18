"""
Metrics evaluation for Tour-resQ Price Engine.
Measures False Positive Rate and Accuracy of the Median/MAD robust detection.
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

import random
from app.engine.price_checker import check_single_price
from app.data.price_db import init_price_db

# Initialize fresh DB for testing
init_price_db()

def measure_pricing_metrics():
    # 1. Test dataset: 
    # True negatives (Fair prices) -> Should be "fair" or "slightly_high"
    fair_prices = [
        ("pho", 35000), ("pho", 45000), ("pho", 55000), ("pho", 65000),
        ("banh_mi", 15000), ("banh_mi", 25000), ("banh_mi", 30000),
        ("pho", 40000), ("banh_mi", 20000),
        ("coffee", 25000), ("coffee", 35000), ("coffee", 40000), ("coffee", 30000),
        ("taxi", 15000), ("taxi", 12000), ("taxi", 18000), ("taxi", 20000),
        ("pho", 50000), ("pho", 60000), ("banh_mi", 18000), ("banh_mi", 22000),
        ("coffee", 28000), ("coffee", 32000), ("taxi", 16000), ("taxi", 14000),
        ("pho", 38000), ("pho", 42000), ("banh_mi", 28000), ("banh_mi", 24000),
        ("coffee", 38000), ("taxi", 17000)
    ]
    
    # True positives (Scam/Overpriced) -> Should be "overpriced" or "slightly_high"
    over_prices = [
        ("pho", 150000), ("pho", 300000), ("pho", 500000),
        ("banh_mi", 120000), ("banh_mi", 150000),
        ("pho", 120000), ("banh_mi", 90000),
        ("coffee", 100000), ("coffee", 150000), ("coffee", 200000),
        ("taxi", 50000), ("taxi", 80000), ("taxi", 100000), ("taxi", 150000),
        ("pho", 200000), ("pho", 250000), ("banh_mi", 100000), ("banh_mi", 180000),
        ("coffee", 120000), ("coffee", 250000), ("taxi", 70000), ("taxi", 120000),
        ("pho", 400000), ("banh_mi", 130000), ("coffee", 180000), ("taxi", 90000)
    ]

    false_positives = 0
    true_negatives = 0
    
    for item, price in fair_prices:
        region = "danang" if "taxi" in item or "coffee" in item else "hanoi"
        res = check_single_price(item, price, region)
        if res.tier in ("overpriced", "slightly_high"):
            false_positives += 1
        else:
            true_negatives += 1

    true_positives = 0
    false_negatives = 0

    for item, price in over_prices:
        region = "danang" if "taxi" in item or "coffee" in item else "hanoi"
        res = check_single_price(item, price, region)
        if res.tier in ("overpriced", "slightly_high"):
            true_positives += 1
        else:
            print(f"Failed to detect: {item} for {price} in {region} -> got {res.tier}")
            false_negatives += 1

    total_fair = len(fair_prices)
    total_over = len(over_prices)

    fpr = (false_positives / total_fair) * 100 if total_fair > 0 else 0
    recall = (true_positives / total_over) * 100 if total_over > 0 else 0
    precision = (true_positives / (true_positives + false_positives)) * 100 if (true_positives + false_positives) > 0 else 0

    print("=========================================")
    print("      TOUR-RESQ METRICS EVALUATION       ")
    print("=========================================")
    print(f"Total Fair Scenarios Tested: {total_fair}")
    print(f"Total Scam Scenarios Tested: {total_over}")
    print("-----------------------------------------")
    print(f"False Positive Rate (FPR): {fpr:.1f}%  (Target: < 5%)")
    print(f"Recall (Scam Detection):   {recall:.1f}%  (Target: > 90%)")
    print(f"Precision:                 {precision:.1f}%  (Target: > 90%)")
    print("=========================================")
    
    if fpr > 5.0:
        print("❌ FAILED: False positive rate is too high! Tourists will be annoyed.")
    elif recall < 90.0:
        print("❌ FAILED: Recall is too low! Scams are slipping through.")
    else:
        print("✅ PASSED: Algorithm meets enterprise standards.")

if __name__ == "__main__":
    measure_pricing_metrics()
