from types import SimpleNamespace


def test_detects_generic_banh_price_above_median(monkeypatch):
    from app.engine import realtime_price_guard

    def fake_check_single_price(item_name, asked_price, region):
        assert item_name == "banh_mi"
        assert asked_price == 30000
        assert region == "hanoi"
        return SimpleNamespace(
            tier="fair",
            median_price=25000,
            price_range="15,000 - 45,000 VND",
            sample_count=5,
            confidence=0.25,
            message="Fair but above median.",
        )

    monkeypatch.setattr(realtime_price_guard, "check_single_price", fake_check_single_price)

    alert = realtime_price_guard.detect_realtime_price_alert(
        original_text="30 nghin dong mot chiec banh",
        translated_text="30 thousand dong for one cake",
        region="hanoi",
    )

    assert alert["should_alert"] is True
    assert alert["tier"] == "above_median"
    assert alert["item_name"] == "banh_mi"
    assert alert["asked_price"] == 30000
    assert alert["quantity"] == 1
    assert "30,000 VND" in alert["message"]
    assert "25,000 VND" in alert["message"]


def test_skips_price_alert_when_item_is_unknown():
    from app.engine.realtime_price_guard import detect_realtime_price_alert

    alert = detect_realtime_price_alert(
        original_text="30 nghin dong",
        translated_text="30 thousand dong",
        region="hanoi",
    )

    assert alert["should_alert"] is False
    assert alert["reason"] == "missing_item_or_price"


def test_detects_overpriced_known_item(monkeypatch):
    from app.engine import realtime_price_guard

    def fake_check_single_price(item_name, asked_price, region):
        return SimpleNamespace(
            tier="overpriced",
            median_price=40000,
            price_range="32,000 - 65,000 VND",
            sample_count=12,
            confidence=0.6,
            message="Significantly overpriced.",
        )

    monkeypatch.setattr(realtime_price_guard, "check_single_price", fake_check_single_price)

    alert = realtime_price_guard.detect_realtime_price_alert(
        original_text="pho 120k",
        translated_text="pho 120k",
        region="hanoi",
    )

    assert alert["should_alert"] is True
    assert alert["tier"] == "overpriced"
    assert alert["item_name"] == "pho"
    assert alert["asked_price"] == 120000


def test_detects_street_banh_mi_price_after_seed_refresh():
    from app.data.price_db import init_price_db
    from app.engine.realtime_price_guard import detect_realtime_price_alert

    init_price_db()

    alert = detect_realtime_price_alert(
        original_text="30 nghin dong mot chiec banh mi",
        translated_text="30 thousand dong for one banh mi",
        region="hanoi",
    )

    assert alert["should_alert"] is True
    assert alert["item_name"] == "banh_mi"
    assert alert["asked_price"] == 30000
    assert alert["median_price"] == 20000
