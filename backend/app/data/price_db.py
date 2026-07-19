"""
Tour-resQ Price Reference Database
===================================
SQLite-backed price database with:
- Regional price references (Hanoi, Da Nang, HCMC, etc.)
- Self-updating mechanism from verified tourist transactions
- Statistical aggregation for anomaly detection

Design: The DB seeds from JSON on first run, then grows from
        community data as tourists verify fair prices.
"""
import sqlite3
import json
import os
import math
import re
import unicodedata
from datetime import datetime, timezone
from typing import Optional
from loguru import logger


if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/tour_resq.db"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "tour_resq.db")

SEED_PATH = os.path.join(os.path.dirname(__file__), "seed_prices.json")


CONVERSATION_OBSERVATIONS_SCHEMA = """
    CREATE TABLE IF NOT EXISTS conversation_observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        message_id TEXT NOT NULL UNIQUE,
        region TEXT NOT NULL,
        speaker TEXT NOT NULL,
        source_lang TEXT NOT NULL,
        target_lang TEXT NOT NULL,
        original_text_scrubbed TEXT DEFAULT '',
        translated_text TEXT DEFAULT '',
        intent TEXT DEFAULT 'unknown',
        item_name TEXT DEFAULT '',
        item_name_vi TEXT DEFAULT '',
        price_vnd INTEGER DEFAULT 0,
        quantity REAL DEFAULT 1.0,
        risk_level TEXT DEFAULT 'none',
        scam_type TEXT DEFAULT '',
        confidence REAL DEFAULT 0.0,
        should_alert BOOLEAN DEFAULT 0,
        should_promote_to_price_db BOOLEAN DEFAULT 0,
        is_verified BOOLEAN DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_conversation_observations_session
        ON conversation_observations(session_id, created_at);

    CREATE INDEX IF NOT EXISTS idx_conversation_observations_item_region
        ON conversation_observations(region, item_name, price_vnd);
"""


def get_db() -> sqlite3.Connection:
    """Get a database connection with WAL mode for concurrent reads."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_conversation_observations_schema(conn: sqlite3.Connection) -> None:
    """Apply the lightweight live-conversation observation schema migration."""
    conn.executescript(CONVERSATION_OBSERVATIONS_SCHEMA)
    conn.commit()


def init_price_db():
    """Initialize the price database and seed with bootstrap data."""
    conn = get_db()
    cursor = conn.cursor()

    # Create tables
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS price_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT NOT NULL,           -- 'hanoi', 'danang', 'hcmc', etc.
            category TEXT NOT NULL,         -- 'food', 'transport', 'drink', 'service'
            item_name TEXT NOT NULL,        -- 'pho', 'taxi_per_km', 'beer_local'
            item_name_vi TEXT,              -- Vietnamese name for matching
            price_vnd INTEGER NOT NULL,     -- Price in VND
            source TEXT DEFAULT 'seed',     -- 'seed', 'tourist_verified', 'grab', 'foody'
            venue_type TEXT DEFAULT 'street', -- 'street', 'restaurant', 'hotel', 'tourist_area'
            is_verified BOOLEAN DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_price_region_category
            ON price_references(region, category, item_name);

        CREATE INDEX IF NOT EXISTS idx_price_region_item
            ON price_references(region, item_name);

        CREATE TABLE IF NOT EXISTS price_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT NOT NULL,
            category TEXT NOT NULL,
            item_name TEXT NOT NULL,
            venue_type TEXT DEFAULT 'all',
            sample_count INTEGER DEFAULT 0,
            mean_price REAL DEFAULT 0,
            std_dev REAL DEFAULT 0,
            median_price REAL DEFAULT 0,
            mad REAL DEFAULT 0,
            min_price INTEGER DEFAULT 0,
            max_price INTEGER DEFAULT 0,
            p25_price INTEGER DEFAULT 0,
            p75_price INTEGER DEFAULT 0,
            last_updated TEXT DEFAULT (datetime('now')),
            UNIQUE(region, category, item_name, venue_type)
        );

        CREATE TABLE IF NOT EXISTS scam_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT,
            scam_type TEXT,
            description TEXT,
            location_lat REAL,
            location_lng REAL,
            language TEXT DEFAULT 'en',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS contribution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            region TEXT NOT NULL,
            created_at DATE DEFAULT CURRENT_DATE
        );
        CREATE INDEX IF NOT EXISTS idx_contribution_logs 
            ON contribution_logs(device_id, item_name, region, created_at);

    """)
    ensure_conversation_observations_schema(conn)

    # Keep the local DB aligned with the seed file without duplicating rows.
    count = cursor.execute("SELECT COUNT(*) FROM price_references").fetchone()[0]
    if os.path.exists(SEED_PATH):
        _seed_database(cursor)
    elif count == 0:
        _seed_inline_defaults(cursor)

    conn.commit()

    # Rebuild stats after seeding
    rebuild_price_stats(conn)

    conn.close()
    logger.info(f"Price DB initialized at {DB_PATH}")


def _seed_database(cursor: sqlite3.Cursor):
    """Seed the database with bootstrap price data."""
    if not os.path.exists(SEED_PATH):
        logger.warning(f"Seed file not found at {SEED_PATH}, using inline defaults")
        _seed_inline_defaults(cursor)
        return

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        seed_data = json.load(f)

    count = 0
    for entry in seed_data:
        exists = cursor.execute("""
            SELECT 1
            FROM price_references
            WHERE region = ?
              AND category = ?
              AND item_name = ?
              AND item_name_vi = ?
              AND price_vnd = ?
              AND source = ?
              AND venue_type = ?
            LIMIT 1
        """, (
            entry["region"],
            entry["category"],
            entry["item_name"],
            entry.get("item_name_vi", ""),
            entry["price_vnd"],
            entry.get("source", "seed"),
            entry.get("venue_type", "street"),
        )).fetchone()
        if exists:
            continue

        cursor.execute("""
            INSERT INTO price_references
                (region, category, item_name, item_name_vi, price_vnd, source, venue_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry["region"],
            entry["category"],
            entry["item_name"],
            entry.get("item_name_vi", ""),
            entry["price_vnd"],
            entry.get("source", "seed"),
            entry.get("venue_type", "street"),
        ))
        count += 1

    if count:
        logger.info(f"Seeded {count} missing price references from {SEED_PATH}")


def _seed_inline_defaults(cursor: sqlite3.Cursor):
    """Fallback inline seed data if JSON file is missing."""
    defaults = [
        # Hanoi food
        ("hanoi", "food", "pho", "phở", 35000, "street"),
        ("hanoi", "food", "pho", "phở", 45000, "restaurant"),
        ("hanoi", "food", "pho", "phở", 65000, "tourist_area"),
        ("hanoi", "food", "banh_mi", "bánh mì", 20000, "street"),
        ("hanoi", "food", "banh_mi", "bánh mì", 35000, "restaurant"),
        ("hanoi", "food", "com_rang", "cơm rang", 35000, "street"),
        ("hanoi", "food", "com_rang", "cơm rang", 55000, "restaurant"),
        ("hanoi", "food", "bun_cha", "bún chả", 40000, "street"),
        ("hanoi", "food", "bun_cha", "bún chả", 60000, "restaurant"),
        # Hanoi drinks
        ("hanoi", "drink", "beer_local", "bia hơi", 10000, "street"),
        ("hanoi", "drink", "beer_local", "bia hơi", 25000, "restaurant"),
        ("hanoi", "drink", "coffee", "cà phê", 20000, "street"),
        ("hanoi", "drink", "coffee", "cà phê", 45000, "restaurant"),
        ("hanoi", "drink", "water_bottle", "nước suối", 8000, "street"),
        ("hanoi", "drink", "smoothie", "sinh tố", 25000, "street"),
        # Hanoi transport
        ("hanoi", "transport", "taxi_per_km", "taxi/km", 14000, "street"),
        ("hanoi", "transport", "grab_bike_per_km", "grab bike/km", 5000, "street"),
        ("hanoi", "transport", "airport_taxi", "taxi sân bay", 350000, "street"),
        # HCMC food
        ("hcmc", "food", "pho", "phở", 40000, "street"),
        ("hcmc", "food", "pho", "phở", 55000, "restaurant"),
        ("hcmc", "food", "banh_mi", "bánh mì", 25000, "street"),
        ("hcmc", "food", "com_tam", "cơm tấm", 35000, "street"),
        ("hcmc", "food", "com_tam", "cơm tấm", 55000, "restaurant"),
        # HCMC drinks
        ("hcmc", "drink", "beer_local", "bia", 15000, "street"),
        ("hcmc", "drink", "coffee", "cà phê", 25000, "street"),
        ("hcmc", "drink", "coffee", "cà phê", 50000, "restaurant"),
        # HCMC transport
        ("hcmc", "transport", "taxi_per_km", "taxi/km", 15000, "street"),
        ("hcmc", "transport", "grab_bike_per_km", "grab bike/km", 5500, "street"),
        ("hcmc", "transport", "airport_taxi", "taxi sân bay", 250000, "street"),
        # Da Nang food
        ("danang", "food", "pho", "phở", 30000, "street"),
        ("danang", "food", "pho", "phở", 50000, "restaurant"),
        ("danang", "food", "banh_mi", "bánh mì", 18000, "street"),
        ("danang", "food", "mi_quang", "mì Quảng", 30000, "street"),
        ("danang", "food", "bun_mam", "bún mắm", 35000, "street"),
        ("danang", "food", "seafood_plate", "hải sản", 150000, "restaurant"),
        # Da Nang drinks
        ("danang", "drink", "beer_local", "bia", 12000, "street"),
        ("danang", "drink", "coffee", "cà phê", 18000, "street"),
        # Da Nang transport
        ("danang", "transport", "taxi_per_km", "taxi/km", 13000, "street"),
        ("danang", "transport", "grab_bike_per_km", "grab bike/km", 4500, "street"),
    ]

    for region, cat, item, vi, price, venue in defaults:
        cursor.execute("""
            INSERT INTO price_references
                (region, category, item_name, item_name_vi, price_vnd, source, venue_type)
            VALUES (?, ?, ?, ?, ?, 'seed', ?)
        """, (region, cat, item, vi, price, venue))

    logger.info(f"Seeded {len(defaults)} inline default prices")


def rebuild_price_stats(conn: Optional[sqlite3.Connection] = None):
    """
    Rebuild aggregate statistics for all region+category+item combinations.
    This is the core of the anomaly detection system.
    """
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True

    cursor = conn.cursor()

    # Clear and rebuild
    cursor.execute("DELETE FROM price_stats")

    cursor.execute("""
        INSERT INTO price_stats (region, category, item_name, venue_type,
                                  sample_count, min_price, max_price)
        SELECT
            region, category, item_name, venue_type,
            COUNT(*) as sample_count,
            MIN(price_vnd) as min_price,
            MAX(price_vnd) as max_price
        FROM price_references
        WHERE is_verified = 1
        GROUP BY region, category, item_name, venue_type
    """)

    # Also compute "all venue types" aggregate
    cursor.execute("""
        INSERT OR REPLACE INTO price_stats
            (region, category, item_name, venue_type,
             sample_count, min_price, max_price)
        SELECT
            region, category, item_name, 'all',
            COUNT(*) as sample_count,
            MIN(price_vnd) as min_price,
            MAX(price_vnd) as max_price
        FROM price_references
        WHERE is_verified = 1
        GROUP BY region, category, item_name
    """)

    # Compute Median, MAD, and Standard Deviation
    rows = cursor.execute("""
        SELECT id, region, category, item_name, venue_type
        FROM price_stats
    """).fetchall()

    for row in rows:
        prices = cursor.execute("""
            SELECT price_vnd FROM price_references
            WHERE region = ? AND category = ? AND item_name = ?
            AND (venue_type = ? OR ? = 'all')
            AND is_verified = 1
        """, (row["region"], row["category"], row["item_name"],
              row["venue_type"], row["venue_type"])).fetchall()

        if len(prices) >= 1:
            sorted_prices = sorted(p["price_vnd"] for p in prices)
            n = len(sorted_prices)
            
            # Median
            if n % 2 == 1:
                median = sorted_prices[n // 2]
            else:
                median = (sorted_prices[n // 2 - 1] + sorted_prices[n // 2]) / 2.0
                
            # Mean and Std Dev
            mean = sum(sorted_prices) / n
            variance = sum((p - mean) ** 2 for p in sorted_prices) / n
            std_dev = math.sqrt(variance)
            
            # MAD (Median Absolute Deviation)
            abs_devs = sorted(abs(p - median) for p in sorted_prices)
            if n % 2 == 1:
                mad = abs_devs[n // 2]
            else:
                mad = (abs_devs[n // 2 - 1] + abs_devs[n // 2]) / 2.0

            p25 = sorted_prices[max(0, n // 4)]
            p75 = sorted_prices[min(n - 1, 3 * n // 4)]

            cursor.execute("""
                UPDATE price_stats
                SET mean_price = ?, std_dev = ?, median_price = ?, mad = ?, 
                    p25_price = ?, p75_price = ?, last_updated = ?
                WHERE id = ?
            """, (mean, std_dev, median, mad, p25, p75, datetime.now(timezone.utc).isoformat(), row["id"]))

    conn.commit()
    if close_conn:
        conn.close()


def get_price_stats(region: str, item_name: str,
                    venue_type: str = "all") -> Optional[dict]:
    """
    Get price statistics for an item in a region.

    Returns:
        Dict with mean, std_dev, min, max, sample_count, etc.
        None if no data found.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Try specific venue type first, fall back to "all"
    row = cursor.execute("""
        SELECT * FROM price_stats
        WHERE region = ? AND item_name = ? AND venue_type = ?
    """, (region, item_name, venue_type)).fetchone()

    if row is None and venue_type != "all":
        row = cursor.execute("""
            SELECT * FROM price_stats
            WHERE region = ? AND item_name = ? AND venue_type = 'all'
        """, (region, item_name)).fetchone()

    conn.close()

    if row is None:
        return None

    return dict(row)


def add_verified_price(region: str, category: str, item_name: str,
                       price_vnd: int, venue_type: str = "street",
                       item_name_vi: str = "", device_id: str = "") -> bool:
    """
    Add a tourist-verified price to the database.
    Checks rate limit per device_id to prevent Sybil attacks/Data poisoning.
    Returns True if added, False if rate limited.
    """
    conn = get_db()
    cursor = conn.cursor()

    if device_id:
        # Check if this device already contributed to this item today
        count = cursor.execute("""
            SELECT COUNT(*) FROM contribution_logs 
            WHERE device_id = ? AND item_name = ? AND region = ? AND created_at = CURRENT_DATE
        """, (device_id, item_name, region)).fetchone()[0]
        
        if count >= 1:
            conn.close()
            logger.warning(f"Sybil attack prevention: Device {device_id} already contributed to {item_name} today.")
            return False

    cursor.execute("""
        INSERT INTO price_references
            (region, category, item_name, item_name_vi, price_vnd,
             source, venue_type, is_verified)
        VALUES (?, ?, ?, ?, ?, 'tourist_verified', ?, 1)
    """, (region, category, item_name, item_name_vi, price_vnd, venue_type))

    if device_id:
        cursor.execute("""
            INSERT INTO contribution_logs (device_id, item_name, region)
            VALUES (?, ?, ?)
        """, (device_id, item_name, region))

    conn.commit()

    # Rebuild stats for this specific item
    rebuild_price_stats(conn)
    conn.close()

    logger.info(f"Added verified price: {item_name} = {price_vnd} VND in {region} by {device_id}")
    return True


def add_ambient_price(region: str, item_name: str, price_vnd: int) -> bool:
    """
    Add a price extracted passively from ambient audio (Live Translation/Guardian).
    Does NOT store device_id to ensure absolute privacy.
    Source is tagged as 'ambient_audio'.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO price_references
            (region, category, item_name, item_name_vi, price_vnd,
             source, venue_type, is_verified)
        VALUES (?, 'food', ?, '', ?, 'ambient_audio', 'street', 1)
    """, (region, item_name, price_vnd))

    conn.commit()
    rebuild_price_stats(conn)
    conn.close()

    logger.info(f"Ambient Price collected anonymously: {item_name} = {price_vnd} VND in {region}")
    return True


def add_ai_crawler_price(region: str, item_name: str, price_vnd: int, source_url: str = "") -> bool:
    """
    Add a price scraped by the AI delivery crawler.
    Source is tagged as 'ai_crawler'.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO price_references
            (region, category, item_name, item_name_vi, price_vnd,
             source, venue_type, is_verified)
        VALUES (?, 'food', ?, ?, ?, 'ai_crawler', 'street', 1)
    """, (region, item_name, source_url, price_vnd)) # using item_name_vi to store source_url temporarily for simplicity

    conn.commit()
    rebuild_price_stats(conn)
    conn.close()
    
    logger.info(f"AI Crawler Price collected: {item_name} = {price_vnd} VND in {region} from {source_url}")
    return True


def search_item(query: str, region: str = "") -> list[dict]:
    """
    Search for items matching a query string.
    Uses fuzzy matching on item_name and item_name_vi.
    """
    def normalize(value: str) -> str:
        value = unicodedata.normalize("NFKD", value or "")
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = value.lower().replace("_", " ")
        return re.sub(r"[^a-z0-9]+", " ", value).strip()

    conn = get_db()
    cursor = conn.cursor()

    query_like = f"%{query.lower()}%"
    if region:
        rows = cursor.execute("""
            SELECT DISTINCT item_name, item_name_vi, category
            FROM price_references
            WHERE region = ?
            AND (LOWER(item_name) LIKE ? OR LOWER(item_name_vi) LIKE ?)
        """, (region, query_like, query_like)).fetchall()
    else:
        rows = cursor.execute("""
            SELECT DISTINCT item_name, item_name_vi, category
            FROM price_references
            WHERE LOWER(item_name) LIKE ? OR LOWER(item_name_vi) LIKE ?
        """, (query_like, query_like)).fetchall()

    if rows:
        conn.close()
        return [dict(r) for r in rows]

    normalized_query = normalize(query)
    query_tokens = set(normalized_query.split())
    if not query_tokens:
        conn.close()
        return []

    if region:
        candidates = cursor.execute("""
            SELECT DISTINCT item_name, item_name_vi, category
            FROM price_references
            WHERE region = ?
        """, (region,)).fetchall()
    else:
        candidates = cursor.execute("""
            SELECT DISTINCT item_name, item_name_vi, category
            FROM price_references
        """).fetchall()

    scored_rows = []
    for row in candidates:
        item_name_norm = normalize(row["item_name"])
        item_vi_norm = normalize(row["item_name_vi"])
        item_tokens = set(item_name_norm.split())
        vi_tokens = set(item_vi_norm.split())

        score = 0
        if item_name_norm and item_name_norm in normalized_query:
            score = max(score, 100 + len(item_tokens))
        if item_vi_norm and item_vi_norm in normalized_query:
            score = max(score, 90 + len(vi_tokens))
        if item_tokens and item_tokens.issubset(query_tokens):
            score = max(score, 70 + len(item_tokens))
        if vi_tokens and vi_tokens.issubset(query_tokens):
            score = max(score, 60 + len(vi_tokens))

        if score:
            scored_rows.append((score, dict(row)))

    conn.close()
    scored_rows.sort(key=lambda item: (-item[0], item[1]["item_name"]))
    return [row for _, row in scored_rows]


def add_conversation_observation(
    session_id: str,
    message_id: str,
    region: str,
    speaker: str,
    source_lang: str,
    target_lang: str,
    original_text_scrubbed: str,
    translated_text: str,
    intent: str,
    item_name: str,
    item_name_vi: str,
    price_vnd: int,
    quantity: float,
    risk_level: str,
    scam_type: str,
    confidence: float,
    should_alert: bool,
    should_promote_to_price_db: bool,
) -> int:
    """Store unverified AI-extracted conversation data for later review/editing."""
    conn = get_db()
    ensure_conversation_observations_schema(conn)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO conversation_observations
            (session_id, message_id, region, speaker, source_lang, target_lang,
             original_text_scrubbed, translated_text, intent, item_name, item_name_vi,
             price_vnd, quantity, risk_level, scam_type, confidence,
             should_alert, should_promote_to_price_db)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        message_id,
        region,
        speaker,
        source_lang,
        target_lang,
        original_text_scrubbed,
        translated_text,
        intent,
        item_name,
        item_name_vi,
        int(price_vnd or 0),
        float(quantity or 1.0),
        risk_level,
        scam_type,
        float(confidence or 0.0),
        1 if should_alert else 0,
        1 if should_promote_to_price_db else 0,
    ))

    conn.commit()
    observation_id = cursor.lastrowid
    conn.close()
    return int(observation_id)


def get_recent_session_observations(session_id: str, limit: int = 10) -> list[dict]:
    """Return recent editable observations for a live conversation session."""
    conn = get_db()
    ensure_conversation_observations_schema(conn)
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT * FROM conversation_observations
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (session_id, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


_OBSERVATION_EDITABLE_FIELDS = {
    "region",
    "speaker",
    "source_lang",
    "target_lang",
    "original_text_scrubbed",
    "translated_text",
    "intent",
    "item_name",
    "item_name_vi",
    "price_vnd",
    "quantity",
    "risk_level",
    "scam_type",
    "confidence",
    "should_alert",
    "should_promote_to_price_db",
    "is_verified",
}


def update_conversation_observation(observation_id: int, **updates) -> bool:
    """Update selected observation fields using a strict allow-list."""
    allowed_updates = {
        key: value for key, value in updates.items()
        if key in _OBSERVATION_EDITABLE_FIELDS
    }
    if not allowed_updates:
        return False

    for key in ("should_alert", "should_promote_to_price_db", "is_verified"):
        if key in allowed_updates:
            allowed_updates[key] = 1 if allowed_updates[key] else 0
    if "price_vnd" in allowed_updates:
        allowed_updates["price_vnd"] = int(allowed_updates["price_vnd"] or 0)
    if "quantity" in allowed_updates:
        allowed_updates["quantity"] = float(allowed_updates["quantity"] or 1.0)
    if "confidence" in allowed_updates:
        allowed_updates["confidence"] = float(allowed_updates["confidence"] or 0.0)

    allowed_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    assignments = ", ".join(f"{key} = ?" for key in allowed_updates)
    values = list(allowed_updates.values()) + [observation_id]

    conn = get_db()
    ensure_conversation_observations_schema(conn)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE conversation_observations SET {assignments} WHERE id = ?",
        values,
    )
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed


def verify_conversation_observation(
    observation_id: int,
    should_promote_to_price_db: bool = False,
) -> bool:
    """Mark an observation as reviewed without automatically changing price references."""
    return update_conversation_observation(
        observation_id,
        is_verified=True,
        should_promote_to_price_db=should_promote_to_price_db,
    )
