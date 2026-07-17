"""
Tour-resQ Authority Router
==========================
Finds the nearest local authority based on GPS coordinates and
generates automated incident reports in Vietnamese.
"""
import math
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Authority:
    name: str
    lat: float
    lng: float
    phone: str
    type: str  # "POLICE" or "TOURISM_BOARD"

# Mock Database of Authorities around Hanoi Old Quarter / Hoan Kiem
AUTHORITIES: List[Authority] = [
    Authority("Công An Phường Hàng Bạc", 21.0333, 105.8525, "024 3825 4104", "POLICE"),
    Authority("Công An Phường Tràng Tiền", 21.0250, 105.8540, "024 3825 7384", "POLICE"),
    Authority("Công An Phường Hàng Gai", 21.0320, 105.8500, "024 3825 4310", "POLICE"),
    Authority("Trung Tâm Hỗ Trợ Khách Du Lịch (Sở DL HN)", 21.0300, 105.8520, "1900 6068", "TOURISM_BOARD")
]

def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance in kilometers between two points on the earth."""
    R = 6371.0 # Earth radius in km

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    
    a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def find_nearest_authority(lat: float, lng: float) -> tuple[Optional[Authority], float]:
    """Finds the nearest authority to the given coordinates."""
    if not AUTHORITIES:
        return None, 0.0
        
    nearest = None
    min_dist = float('inf')
    
    for auth in AUTHORITIES:
        dist = _haversine_distance(lat, lng, auth.lat, auth.lng)
        if dist < min_dist:
            min_dist = dist
            nearest = auth
            
    return nearest, min_dist

def generate_official_report_vi(
    timestamp: str,
    lat: float,
    lng: float,
    scam_type: str,
    details: str,
    audio_signature: str
) -> str:
    """
    Translates and formats the incident into a formal Vietnamese report for the police.
    """
    report = f"""
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
--------------------------------

BÁO CÁO VI PHẠM AN NINH DU LỊCH (Tự động tạo bởi Tour-resQ)
Thời gian ghi nhận: {timestamp}
Tọa độ sự cố: {lat:.6f}, {lng:.6f}

1. Lĩnh vực vi phạm: {scam_type}
2. Tóm tắt sự việc: Trí tuệ nhân tạo phát hiện hành vi ép giá / lừa đảo đối với khách du lịch nước ngoài. Chi tiết trích xuất:
"{details}"

3. Bằng chứng đính kèm: 
- Bản ghi âm bảo mật (Mã Hash: {audio_signature})
- Dữ liệu định vị GPS theo thời gian thực.

Kính đề nghị cơ quan chức năng kiểm tra và xử lý.
"""
    return report.strip()
