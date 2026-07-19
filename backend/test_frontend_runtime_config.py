from pathlib import Path


def test_frontend_uses_same_origin_api_for_local_testing():
    app_js = Path(__file__).resolve().parents[1] / "frontend" / "app.js"
    source = app_js.read_text(encoding="utf-8")

    assert "const API_BASE = window.__TOUR_RESQ_API_BASE || window.location.origin;" in source
    assert "tour-resq-production.up.railway.app" not in source


def test_translate_tab_has_manual_text_path_and_cache_bust():
    project_root = Path(__file__).resolve().parents[1]
    index_html = (project_root / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (project_root / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "tourist-manual-input" in index_html
    assert "vendor-manual-input" in index_html
    assert "styles.css?v=35" in index_html
    assert "app.js?v=35" in index_html
    assert "window.sendManualLiveMessage" in app_js
    assert "data.price_alert?.should_alert" in app_js
    assert "PRICE WARNING" in app_js
    assert "lastPriceWarningAt" in app_js
    assert "warningIsFresh" in app_js


def test_frontend_has_safe_external_dependency_fallbacks():
    project_root = Path(__file__).resolve().parents[1]
    index_html = (project_root / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (project_root / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "if (window.feather) feather.replace();" in index_html
    assert "AbortController" in app_js
    assert "reverseController.abort()" in app_js


def test_sos_slide_starts_loud_siren_and_cancel_stops_it():
    project_root = Path(__file__).resolve().parents[1]
    app_js = (project_root / "frontend" / "app.js").read_text(encoding="utf-8")
    styles_css = (project_root / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert "function startSOSSiren()" in app_js
    assert "function stopSOSSiren()" in app_js
    assert "window.AudioContext || window.webkitAudioContext" in app_js
    assert "sosMasterGain.gain.setValueAtTime(0.95" in app_js
    assert "startSOSSiren();" in app_js
    assert "stopSOSSiren();" in app_js
    assert "sos-siren-active" in app_js
    assert "@keyframes sos-flash" in styles_css
