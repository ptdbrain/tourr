import re
import time
import unicodedata

from app.engine.price_checker import check_single_price


ABOVE_MEDIAN_RATIO = 1.15

ITEM_ALIASES = [
    ("banh_trang_tron", "banh trang tron", ["banh trang tron", "rice paper salad"]),
    ("banh_xeo", "banh xeo", ["banh xeo", "vietnamese pancake"]),
    ("banh_bao", "banh bao", ["banh bao", "steamed bun"]),
    ("banh_gio", "banh gio", ["banh gio"]),
    ("banh_mi", "banh mi", ["banh mi", "sandwich", "bread", "cake", "banh"]),
    ("bun_cha", "bun cha", ["bun cha"]),
    ("pho", "pho", ["pho", "noodle soup"]),
    ("com_tam", "com tam", ["com tam", "broken rice"]),
    ("com_rang", "com rang", ["com rang", "fried rice"]),
    ("coffee", "coffee", ["ca phe", "coffee"]),
    ("water_bottle", "bottled water", ["nuoc suoi", "bottled water", "water bottle"]),
    ("taxi_per_km", "taxi per km", ["taxi", "taxi per km"]),
]

NUMBER_WORDS = {
    "mot": 1,
    "hai": 2,
    "ba": 3,
    "bon": 4,
    "tu": 4,
    "nam": 5,
    "lam": 5,
    "sau": 6,
    "bay": 7,
    "tam": 8,
    "chin": 9,
    "muoi": 10,
}


def _empty_alert(reason: str = "missing_item_or_price") -> dict:
    return {
        "should_alert": False,
        "reason": reason,
        "tier": "none",
        "item_name": "",
        "item_label": "",
        "asked_price": 0,
        "unit_price": 0,
        "quantity": 1,
        "median_price": 0,
        "price_range": "",
        "sample_count": 0,
        "confidence": 0.0,
        "message": "",
        "latency_ms": 0,
    }


def _normalize_text(text: str) -> str:
    value = text.replace("\u0111", "d").replace("\u0110", "D")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    return re.sub(r"\s+", " ", value).strip()


def _parse_number_token(value: str) -> float:
    value = value.strip().replace(",", ".")
    if "." in value:
        left, right = value.split(".", 1)
        if len(right) == 3 and left.isdigit() and right.isdigit():
            return float(left + right)
    return float(value)


def _parse_vietnamese_number_words(text: str) -> int:
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\s+(?:nghin|ngan|k)\b", text):
            return value * 1000

    for tens_word, tens_value in NUMBER_WORDS.items():
        if tens_value < 2:
            continue
        for ones_word, ones_value in NUMBER_WORDS.items():
            phrase = rf"\b{tens_word}\s+muoi(?:\s+{ones_word})?\s+(?:nghin|ngan|k)\b"
            match = re.search(phrase, text)
            if match:
                return (tens_value * 10 + (ones_value if ones_word in match.group(0).split() else 0)) * 1000

    return 0


def _extract_price_vnd(text: str) -> int:
    unit_match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan)\b", text)
    if unit_match:
        return int(_parse_number_token(unit_match.group(1)) * 1000)

    word_price = _parse_vietnamese_number_words(text)
    if word_price:
        return word_price

    full_amount = re.search(r"\b(\d{1,3}(?:[.,]\d{3})+|\d{4,})\s*(?:vnd|dong)?\b", text)
    if full_amount:
        return int(_parse_number_token(full_amount.group(1)))

    shorthand = re.search(r"\b(?:gia|price|cost|tien|dong)\s*(?:la|is)?\s*(\d{2,3})\b", text)
    if shorthand:
        return int(shorthand.group(1)) * 1000

    return 0


def _extract_quantity(text: str) -> float:
    digit_match = re.search(r"\b(\d+)\s*(?:cai|chiec|to|bat|ly|chai|phan|dia|suat|coc|goi|km)\b", text)
    if digit_match:
        return max(1.0, float(digit_match.group(1)))

    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\s+(?:cai|chiec|to|bat|ly|chai|phan|dia|suat|coc|goi|km)\b", text):
            return float(value)

    return 1.0


def _detect_item(text: str) -> tuple[str, str]:
    for item_name, item_label, aliases in ITEM_ALIASES:
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", text):
                return item_name, item_label
    return "", ""


def _format_vnd(value: float) -> str:
    return f"{int(round(value)):,} VND"


def _check_realtime_price(item_name: str, unit_price: float, region: str):
    try:
        return check_single_price(item_name, unit_price, region, "street")
    except TypeError:
        return check_single_price(item_name, unit_price, region)


def detect_realtime_price_alert(
    original_text: str,
    translated_text: str,
    region: str = "hanoi",
) -> dict:
    started_at = time.perf_counter()
    combined = _normalize_text(f"{original_text} {translated_text}")
    item_name, item_label = _detect_item(combined)
    total_price = _extract_price_vnd(combined)
    quantity = _extract_quantity(combined)

    if not item_name or total_price <= 0:
        alert = _empty_alert()
        alert["latency_ms"] = round((time.perf_counter() - started_at) * 1000)
        return alert

    unit_price = total_price / max(quantity, 1.0)

    try:
        price_check = _check_realtime_price(item_name, unit_price, region)
    except Exception as exc:
        alert = _empty_alert("price_check_failed")
        alert["message"] = str(exc)
        alert["latency_ms"] = round((time.perf_counter() - started_at) * 1000)
        return alert

    median_price = float(getattr(price_check, "median_price", 0) or 0)
    db_tier = getattr(price_check, "tier", "insufficient_data")
    should_alert = db_tier in {"slightly_high", "overpriced"}
    alert_tier = db_tier
    reason = db_tier

    if not should_alert and median_price > 0 and unit_price > median_price * ABOVE_MEDIAN_RATIO:
        should_alert = True
        alert_tier = "above_median"
        reason = "above_median"

    if not should_alert:
        alert = _empty_alert("within_normal_range" if median_price > 0 else "insufficient_data")
        alert.update({
            "item_name": item_name,
            "item_label": item_label,
            "asked_price": int(total_price),
            "unit_price": int(round(unit_price)),
            "quantity": quantity,
            "median_price": int(round(median_price)),
            "price_range": getattr(price_check, "price_range", ""),
            "sample_count": int(getattr(price_check, "sample_count", 0) or 0),
            "confidence": float(getattr(price_check, "confidence", 0.0) or 0.0),
            "latency_ms": round((time.perf_counter() - started_at) * 1000),
        })
        return alert

    quantity_text = f"{quantity:g}"
    if alert_tier == "overpriced":
        prefix = "This looks significantly overpriced."
    elif alert_tier == "slightly_high":
        prefix = "This price is above the normal range."
    else:
        prefix = "This price may be higher than usual."

    message = (
        f"{prefix} {_format_vnd(unit_price)} for {quantity_text} {item_label} "
        f"is above the usual {_format_vnd(median_price)} in {region}."
    )

    return {
        "should_alert": True,
        "reason": reason,
        "tier": alert_tier,
        "item_name": item_name,
        "item_label": item_label,
        "asked_price": int(total_price),
        "unit_price": int(round(unit_price)),
        "quantity": quantity,
        "median_price": int(round(median_price)),
        "price_range": getattr(price_check, "price_range", ""),
        "sample_count": int(getattr(price_check, "sample_count", 0) or 0),
        "confidence": float(getattr(price_check, "confidence", 0.0) or 0.0),
        "message": message,
        "latency_ms": round((time.perf_counter() - started_at) * 1000),
    }
