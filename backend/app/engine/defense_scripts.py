"""
Tour-resQ Active Defense Generator
==================================
Generates localized, polite but firm de-escalation scripts in Vietnamese
for the user to play out loud when facing extortion or severe overcharging.
"""

def generate_defense_script(
    tier: str, 
    typology: str, 
    fair_price: float, 
    asked_price: float,
    item_name: str
) -> str:
    """
    Generates a Vietnamese defensive script based on the severity and scam typology.
    """
    if tier == "FAIR" or tier == "BESPOKE_ART":
        return "" # No defense needed
        
    if tier == "PREMIUM":
        # Mild negotiation script
        price_str = f"{int(fair_price):,} đồng"
        return f"Xin lỗi, giá này hơi cao. Tôi có thể trả {price_str} cho {item_name} được không?"
        
    if tier == "EXTREME_OVERCHARGE":
        # Firm de-escalation script
        price_str = f"{int(fair_price):,} đồng"
        asked_str = f"{int(asked_price):,} đồng"
        
        # Specific typology handling
        if "Donut" in typology or "Street Vendor" in typology:
            return f"Tôi biết giá gốc của {item_name} chỉ khoảng {price_str}. Yêu cầu {asked_str} là quá vô lý. Vui lòng nhận {price_str} hoặc tôi sẽ trả lại hàng."
            
        elif "Taxi" in typology:
            return f"Đồng hồ nhảy giá bất thường. Đoạn đường này bình thường chỉ tốn khoảng {price_str}. Nếu bạn ép giá {asked_str}, tôi sẽ gọi cảnh sát 113 hoặc tổng đài du lịch ngay bây giờ."
            
        elif "Shoe" in typology:
            return f"Tôi không yêu cầu dịch vụ này với giá {asked_str}. Tôi chỉ trả đúng {price_str} như đã thỏa thuận ban đầu. Vui lòng trả lại đồ cho tôi."
            
        else:
            # Generic firm response
            return f"Tôi biết mặt bằng giá ở đây chỉ khoảng {price_str}. Việc bạn lấy {asked_str} là không hợp lý. Xin lỗi, tôi không mua."
            
    return ""
