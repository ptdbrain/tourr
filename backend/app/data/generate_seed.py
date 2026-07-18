import json
import os

# Comprehensive lists of items with baseline prices
# Format: (item_name, item_name_vi, category, baseline_price)
ITEMS = [
    # --- STREET FOOD / SNACKS ---
    ("pho", "phở", "food", 35000),
    ("banh_mi", "bánh mì", "food", 20000),
    ("bun_cha", "bún chả", "food", 40000),
    ("bun_dau_mam_tom", "bún đậu mắm tôm", "food", 35000),
    ("xoi", "xôi", "food", 15000),
    ("banh_bao", "bánh bao", "food", 15000),
    ("banh_gio", "bánh giò", "food", 15000),
    ("banh_trang_tron", "bánh tráng trộn", "food", 20000),
    ("nem_chua_ran", "nem chua rán", "food", 50000),  # per plate
    ("ngo_nuong", "ngô nướng", "food", 10000),
    ("khoai_nuong", "khoai nướng", "food", 15000),
    ("com_rang", "cơm rang", "food", 35000),
    ("com_tam", "cơm tấm", "food", 35000),
    ("hu_tieu", "hủ tiếu", "food", 30000),
    ("mi_quang", "mì quảng", "food", 30000),
    ("banh_xeo", "bánh xèo", "food", 40000),
    ("nem_cuon", "gỏi cuốn", "food", 10000),
    
    # --- DRINKS ---
    ("iced_tea", "trà đá", "drink", 3000),
    ("sugar_cane_juice", "nước mía", "drink", 10000),
    ("coconut_water", "nước dừa", "drink", 25000),
    ("lemon_tea", "trà chanh", "drink", 15000),
    ("black_coffee", "cà phê đen", "drink", 15000),
    ("milk_coffee", "cà phê sữa đá", "drink", 20000),
    ("smoothie", "sinh tố", "drink", 25000),
    ("local_beer", "bia hơi", "drink", 10000),
    ("bottled_water", "nước suối", "drink", 5000),
    
    # --- SOUVENIRS (Base prices for average quality) ---
    ("conical_hat", "nón lá", "souvenir", 40000),
    ("t_shirt", "áo phông", "souvenir", 100000),
    ("national_flag", "cờ việt nam", "souvenir", 20000),
    ("keychain", "móc khóa", "souvenir", 15000),
    ("magnet", "nam châm gắn tủ lạnh", "souvenir", 20000),
    ("silk_scarf", "khăn lụa", "souvenir", 150000),
    ("coffee_beans_500g", "cà phê hạt 500g", "souvenir", 150000),
    ("ceramic_cup", "cốc gốm", "souvenir", 80000),
    ("wood_carving", "đồ gỗ khắc", "souvenir", 200000),
    
    # --- SERVICES & TRANSPORT ---
    ("shoe_shine", "đánh giày", "service", 20000),
    ("cyclo_ride_1h", "xích lô 1 giờ", "service", 150000),
    ("photo_with_vendor", "chụp ảnh cùng gánh hàng", "service", 20000),
    ("motorbike_taxi_per_km", "xe ôm / km", "transport", 10000),
    ("taxi_per_km", "taxi / km", "transport", 15000),
]

# Multipliers based on venue/context
VENUE_MULTIPLIERS = {
    "street": 1.0,
    "restaurant": 1.8,       # Restaurants are ~80% more expensive than street
    "tourist_area": 2.5,     # High-end tourist traps/prime locations
    "airport": 3.0,
    "souvenir_shop": 1.5,
    "boutique": 3.0          # High-end souvenir
}

# Regional adjustments (Hanoi is base 1.0)
REGIONS = {
    "hanoi": 1.0,
    "hcmc": 1.1,      # Slightly more expensive
    "danang": 0.9,    # Slightly cheaper
    "hoian": 1.2,     # Tourist town
    "phuquoc": 1.5    # Island pricing
}

seed_data = []

for region, r_mult in REGIONS.items():
    for item_name, item_vi, cat, base_price in ITEMS:
        # Determine applicable venues based on category
        if cat in ("food", "drink"):
            venues = ["street", "restaurant", "tourist_area", "airport"]
        elif cat == "souvenir":
            venues = ["street", "souvenir_shop", "boutique", "tourist_area"]
        elif cat in ("service", "transport"):
            venues = ["street", "tourist_area"]
            
        for venue in venues:
            # Add some slight variation logic
            # e.g., street food in Hoian is 1.2 * 1.0 = 1.2x
            v_mult = VENUE_MULTIPLIERS[venue]
            
            # Special case: some things don't scale as hard
            if cat == "transport" and venue == "tourist_area":
                v_mult = 2.0  # Taxi in tourist area is only double, not 2.5
                
            final_price = int(base_price * r_mult * v_mult)
            # Round to nearest 5000 VND (except for very cheap things)
            if final_price > 20000:
                final_price = round(final_price / 5000) * 5000
            elif final_price > 10000:
                final_price = round(final_price / 1000) * 1000
                
            # Create minimum 3 samples to satisfy MIN_SAMPLE_SIZE automatically
            # We add slight variations (-10%, +0%, +10%)
            variations = [0.9, 1.0, 1.1]
            for var in variations:
                var_price = int(final_price * var)
                # Round again
                if var_price > 10000:
                    var_price = round(var_price / 1000) * 1000
                
                seed_data.append({
                    "region": region,
                    "category": cat,
                    "item_name": item_name,
                    "item_name_vi": item_vi,
                    "price_vnd": var_price,
                    "source": "seed_comprehensive",
                    "venue_type": venue
                })

# Save the JSON
output_path = os.path.join(os.path.dirname(__file__), "seed_prices.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(seed_data, f, ensure_ascii=False, indent=2)

print(f"Successfully generated {len(seed_data)} price references across {len(REGIONS)} regions and {len(ITEMS)} base items.")

# Now we need to rebuild the DB
db_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "tour_resq.db")
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted old database at {db_path}")

# Import and init
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from backend.app.data.price_db import init_price_db

init_price_db()
print("Database re-initialized with new comprehensive seed data.")
