import json
import os
from datetime import datetime
from typing import List, Dict

# Use a local JSON file to simulate a secure Blackbox Database
BLACKBOX_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "blackbox_logs.json")

def ensure_db():
    if not os.path.exists(os.path.dirname(BLACKBOX_DB_PATH)):
        os.makedirs(os.path.dirname(BLACKBOX_DB_PATH))
    if not os.path.exists(BLACKBOX_DB_PATH):
        with open(BLACKBOX_DB_PATH, "w", encoding="utf-8") as f:
            # Seed with some mock hotspot data (around Hanoi Hoan Kiem / Old Quarter)
            seed_data = [
                {"timestamp": "2026-07-10T10:00:00Z", "lat": 21.0315, "lng": 105.8522, "severity": "HIGH", "type": "Donut Extortion"},
                {"timestamp": "2026-07-12T14:30:00Z", "lat": 21.0320, "lng": 105.8510, "severity": "HIGH", "type": "Shoe Shine Scam"},
                {"timestamp": "2026-07-15T19:45:00Z", "lat": 21.0285, "lng": 105.8542, "severity": "CRITICAL", "type": "Fake Taxi"},
                {"timestamp": "2026-07-16T21:10:00Z", "lat": 21.0335, "lng": 105.8505, "severity": "HIGH", "type": "Menu Forgery"},
            ]
            json.dump(seed_data, f, indent=4)

def log_incident(lat: float, lng: float, severity: str, scam_type: str, audio_signature: str = "encrypted_hash"):
    """
    Simulates logging an encrypted incident report to the secure Blackbox.
    """
    ensure_db()
    with open(BLACKBOX_DB_PATH, "r+", encoding="utf-8") as f:
        data = json.load(f)
        new_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "lat": lat,
            "lng": lng,
            "severity": severity,
            "type": scam_type,
            "audio_signature": audio_signature # Proves audio was captured
        }
        data.append(new_record)
        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()
        
    return True

def get_heatmap_data() -> List[Dict]:
    """
    Returns aggregated GPS coordinates for the Heatmap frontend.
    Only returns location and severity to protect victim privacy.
    """
    ensure_db()
    with open(BLACKBOX_DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Filter and format for heatmap
    return [{"lat": item["lat"], "lng": item["lng"], "weight": 1.0 if item["severity"] == "HIGH" else 2.0} for item in data]
