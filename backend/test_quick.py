"""Quick test for Tour-resQ backend components."""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

# Test 1: Price DB init
print("=== Test 1: Price DB ===")
from app.data.price_db import init_price_db
init_price_db()
print("DB initialized OK")

# Test 2: Price checker
print("\n=== Test 2: Price Checker ===")
from app.engine.price_checker import check_single_price

v = check_single_price("pho", 120000, "hanoi")
print(f"Pho 120k VND in Hanoi: tier={v.tier}, z_score={v.z_score}, mean={v.mean_price}")
assert v.tier in ("overpriced", "slightly_high"), f"Expected overpriced, got {v.tier}"

v2 = check_single_price("pho", 40000, "hanoi")
print(f"Pho 40k VND in Hanoi: tier={v2.tier}, z_score={v2.z_score}, mean={v2.mean_price}")
assert v2.tier == "fair", f"Expected fair, got {v2.tier}"

# Test 3: Scam detector
print("\n=== Test 3: Scam Detector ===")
from app.engine.scam_detector import detect_scam_patterns

r = detect_scam_patterns("The taxi meter was going too fast and the driver took a detour", "en")
print(f"Detected: {r.detected}, severity: {r.severity}")
print(f"Patterns: {[p['id'] for p in r.patterns]}")
assert r.detected, "Should detect taxi scam"

r2 = detect_scam_patterns("택시 미터기가 이상해요 기사가 돌아가고 있어요", "ko")
print(f"Korean input - Detected: {r2.detected}, patterns: {[p['id'] for p in r2.patterns]}")

r3 = detect_scam_patterns("I had a nice bowl of pho", "en")
print(f"Normal text - Detected: {r3.detected}")
assert not r3.detected, "Should NOT detect scam for normal text"

# Test 4: i18n
print("\n=== Test 4: i18n ===")
from app.i18n.translations import t, get_supported_languages

print(f"EN: {t('price.fair', 'en')}")
print(f"KO: {t('price.fair', 'ko')}")
print(f"ZH: {t('price.fair', 'zh')}")
print(f"RU: {t('price.fair', 'ru')}")
print(f"Parameterized: {t('price.based_on', 'en', count=147)}")

langs = get_supported_languages()
print(f"Languages: {[l['code'] for l in langs]}")

print("\n✅ ALL TESTS PASSED!")
