from app.data.price_db import init_price_db, search_item


def test_search_item_matches_ocr_english_variants():
    init_price_db()

    pho_results = search_item("Beef Pho", "hanoi")
    tea_results = search_item("Iced Tea", "hanoi")

    assert pho_results
    assert pho_results[0]["item_name"] == "pho"
    assert tea_results
    assert tea_results[0]["item_name"] == "iced_tea"


def test_init_price_db_keeps_seed_data_current_without_duplicates():
    from app.data.price_db import get_db

    init_price_db()
    conn = get_db()
    first_count = conn.execute(
        "SELECT COUNT(*) FROM price_references WHERE item_name = 'iced_tea'"
    ).fetchone()[0]
    conn.close()

    init_price_db()
    conn = get_db()
    second_count = conn.execute(
        "SELECT COUNT(*) FROM price_references WHERE item_name = 'iced_tea'"
    ).fetchone()[0]
    conn.close()

    assert first_count > 0
    assert second_count == first_count


def test_ocr_price_check_uses_dict_search_results_for_lookup(monkeypatch):
    import asyncio
    import base64
    import json

    from app.engine import price_checker

    class FakeModels:
        def generate_content(self, **kwargs):
            class Response:
                text = json.dumps({
                    "items": [{
                        "item_name": "Beef Pho",
                        "item_name_vi": "Pho Bo",
                        "price_vnd": 100000,
                        "quantity": 2,
                        "unit": "item",
                    }],
                    "currency_detected": "VND",
                    "language_detected": "en",
                })

            return Response()

    class FakeClient:
        models = FakeModels()

    init_price_db()
    monkeypatch.setattr(price_checker.settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(price_checker.genai, "Client", lambda api_key: FakeClient())

    result = asyncio.run(price_checker.check_price_from_image(
        image_base64=base64.b64encode(b"fake-image").decode("ascii"),
        region="hanoi",
        lang="en",
    ))

    assert result is not None
    assert result.items_checked[0]["item_name"] == "Beef Pho"
    assert result.items_checked[0]["db_median_price"] > 0
    assert result.items_checked[0]["db_tier"] != "insufficient_data"


def test_ocr_price_check_summary_mentions_slightly_high_items(monkeypatch):
    import asyncio
    import base64
    import json

    from app.engine import price_checker

    class FakeModels:
        def generate_content(self, **kwargs):
            class Response:
                text = json.dumps({
                    "items": [
                        {
                            "item_name": "Special Beef Pho",
                            "item_name_vi": "Pho bo dac biet",
                            "price_vnd": 120000,
                            "quantity": 1,
                            "unit": "item",
                        },
                        {
                            "item_name": "Iced Tea",
                            "item_name_vi": "Tra da",
                            "price_vnd": 10000,
                            "quantity": 1,
                            "unit": "item",
                        },
                    ],
                    "currency_detected": "VND",
                    "language_detected": "en",
                })

            return Response()

    class FakeClient:
        models = FakeModels()

    init_price_db()
    monkeypatch.setattr(price_checker.settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(price_checker.genai, "Client", lambda api_key: FakeClient())

    result = asyncio.run(price_checker.check_price_from_image(
        image_base64=base64.b64encode(b"fake-image").decode("ascii"),
        region="hanoi",
        lang="en",
    ))

    assert result is not None
    assert result.overall_verdict == "slightly_high"
    assert "slightly high" in result.summary.lower()
    assert "fairly priced" not in result.summary.lower()
