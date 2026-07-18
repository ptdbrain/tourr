import re

with open("frontend/app.js", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix analyzeScam
old_analyze_scam = """window.analyzeScam = async function() {
    const text = document.getElementById('incident-input').value;
    if (!text) return;
    const overlay = document.getElementById('scam-results-overlay');
    overlay.style.display = 'flex';
    document.getElementById('guardian-alert-title').innerText = "AI ANALYSIS";
    document.getElementById('guardian-alert-msg').innerText = "Based on your description, this might be a scam. Be careful.";
};"""

new_analyze_scam = """window.analyzeScam = async function() {
    const text = document.getElementById('incident-input').value;
    if (!text) return;
    const overlay = document.getElementById('scam-results-overlay');
    overlay.style.display = 'flex';
    document.getElementById('guardian-alert-title').innerText = "ANALYZING...";
    document.getElementById('guardian-alert-msg').innerText = "Please wait, AI is analyzing the situation...";
    
    try {
        const region = getRegionFromCoordinates(userLocation.lat, userLocation.lng);
        const res = await fetch(API_BASE + '/api/v1/analyze-situation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description: text, language: currentLang, region: region })
        });
        const data = await res.json();
        
        if (data.status === 'success' && data.result) {
            document.getElementById('guardian-alert-title').innerText = data.result.detected ? "SCAM DETECTED" : "AI ANALYSIS";
            document.getElementById('guardian-alert-msg').innerText = data.result.ai_analysis || "Be careful with your belongings and negotiate clearly.";
        } else {
            document.getElementById('guardian-alert-title').innerText = "ERROR";
            document.getElementById('guardian-alert-msg').innerText = "Could not analyze the situation.";
        }
    } catch(e) {
        document.getElementById('guardian-alert-title').innerText = "ERROR";
        document.getElementById('guardian-alert-msg').innerText = "Network Error.";
    }
};"""
content = content.replace(old_analyze_scam, new_analyze_scam)

# 2. Fix OCR region
old_ocr = "body: JSON.stringify({ image_base64: base64Image, language: currentLang, lat: userLocation.lat, lng: userLocation.lng })"
new_ocr = "body: JSON.stringify({ image_base64: base64Image, language: currentLang, region: getRegionFromCoordinates(userLocation.lat, userLocation.lng) })"
content = content.replace(old_ocr, new_ocr)

# 3. Fix contributePrice
old_contribute = """region: "hanoi", category: "food", item_name: item.item_name, item_name_vi: item.item_name_vi,
                    price_vnd: Math.round(item.unit_price), venue_type: "street", device_id: 'dev123'"""
new_contribute = """region: getRegionFromCoordinates(userLocation.lat, userLocation.lng), category: "food", item_name: item.item_name, item_name_vi: item.item_name_vi,
                    price_vnd: Math.round(item.unit_price), venue_type: "street", device_id: 'dev123'"""
content = content.replace(old_contribute, new_contribute)

# 4. Add TTS to handleMessage
old_handle_msg = """        if (data.translated) document.getElementById(tgtEl).textContent = data.translated;"""
new_handle_msg = """        if (data.translated) {
            document.getElementById(tgtEl).textContent = data.translated;
            if (window.speechSynthesis) {
                const utterance = new SpeechSynthesisUtterance(data.translated);
                utterance.lang = tgt === 'vi' ? 'vi-VN' : tgt === 'ko' ? 'ko-KR' : tgt === 'zh' ? 'zh-CN' : 'en-US';
                window.speechSynthesis.speak(utterance);
            }
        }"""
content = content.replace(old_handle_msg, new_handle_msg)

# 5. Append Utils & Dispatch
utils = """
// ── 7. UTILS & REPORTING ──────────────────────────────────
function getRegionFromCoordinates(lat, lng) {
    if (lat > 20.5 && lat < 21.5 && lng > 105.0 && lng < 106.5) return 'hanoi';
    if (lat > 15.5 && lat < 16.5 && lng > 107.5 && lng < 108.5) return 'danang';
    if (lat > 10.0 && lat < 11.0 && lng > 106.0 && lng < 107.0) return 'hcm';
    if (lat > 15.0 && lat < 16.0 && lng > 108.0 && lng < 108.5) return 'hoian';
    if (lat > 12.0 && lat < 12.5 && lng > 109.0 && lng < 109.5) return 'nhatrang';
    if (lat > 10.0 && lat < 10.5 && lng > 103.5 && lng < 104.5) return 'phuquoc';
    return 'hanoi'; // Default
}

window.dispatchReport = async function() {
    if (navigator.vibrate) navigator.vibrate(100);
    const btn = document.querySelector('.btn-dispatch');
    if (btn) { btn.innerHTML = "SENDING..."; btn.disabled = true; }
    
    try {
        await fetch(API_BASE + '/api/v1/dispatch-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: userLocation.lat, lng: userLocation.lng, location_name: userLocation.name,
                incident_type: "scam_report", language: currentLang, severity: "medium", evidence: window.evidenceBuffer
            })
        });
        if (btn) { btn.innerHTML = "SENT TO POLICE"; btn.style.background = 'var(--neon-green)'; btn.style.color = 'black'; }
        window.evidenceBuffer = { images: [], transcripts: [] };
    } catch(e) {
        if (btn) { btn.innerHTML = "FAILED. TRY SOS."; }
    }
};
"""
if "function getRegionFromCoordinates" not in content:
    content += utils

with open("frontend/app.js", "w", encoding="utf-8") as f:
    f.write(content)
print("app.js patched successfully.")
