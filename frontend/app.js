/**
 * Tour-resQ Frontend -- Premium Flow
 * Real API Integration with new Permission & Location Reveal flow.
 */

const API_BASE = '';
let currentLang = localStorage.getItem('tour_resq_lang') || document.documentElement.getAttribute('data-lang') || 'en';

// Global Evidence Buffer
window.evidenceBuffer = {
    images: [], // Suspicious bills
    transcripts: [] // Conversation logs
};

let userLocation = { lat: 21.0285, lng: 105.8542, name: "Unknown Location" };
let cameraStream = null;

document.addEventListener('DOMContentLoaded', () => {
    initSlideToSOS();
    updateLanguageUI(currentLang);
    loadTranslations(currentLang);
    initGlobalMap();
    initRippleEffect();
});

// ── 0.1 GLOBAL MAP (LEAFLET) ──────────────────────────────────
let globalMap = null;
function initGlobalMap() {
    if (typeof L === 'undefined') return;
    const mapEl = document.getElementById('global-map-bg');
    if (!mapEl) return;

    globalMap = L.map('global-map-bg', {
        zoomControl: false, attributionControl: false, dragging: false,
        touchZoom: false, doubleClickZoom: false, scrollWheelZoom: false,
        boxZoom: false, keyboard: false
    }).setView([21.0285, 105.8542], 14);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { subdomains: 'abcd', maxZoom: 20 }).addTo(globalMap);
}

// ── 0.2 RIPPLE EFFECT ─────────────────────────────────────────
function initRippleEffect() {
    document.addEventListener('click', function (e) {
        const target = e.target.closest('button, .lang-btn, .giant-contact-btn');
        if (!target) return;
        const circle = document.createElement('span');
        const diameter = Math.max(target.clientWidth, target.clientHeight);
        const radius = diameter / 2;
        const rect = target.getBoundingClientRect();
        circle.style.width = circle.style.height = `${diameter}px`;
        circle.style.left = `${e.clientX - rect.left - radius}px`;
        circle.style.top = `${e.clientY - rect.top - radius}px`;
        circle.classList.add('ripple-circle');
        const existingRipple = target.querySelector('.ripple-circle');
        if (existingRipple) existingRipple.remove();
        target.appendChild(circle);
        target.classList.add('btn-ripple');
        setTimeout(() => { circle.remove(); }, 600);
    });
}

// ── 0.3 LANGUAGES ─────────────────────────────
let translations = {};
async function loadTranslations(lang) {
    try {
        const res = await fetch(API_BASE + `/api/v1/translations?lang=${lang}`);
        const data = await res.json();
        if (data.status === 'success') { translations = data.translations; applyTranslations(); }
    } catch(e) {}
}
function applyTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (translations[key]) {
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.placeholder = translations[key];
            else el.innerText = translations[key];
        }
    });
}
window.selectLanguage = function(lang) {
    if (navigator.vibrate) navigator.vibrate(20);
    currentLang = lang;
    localStorage.setItem('tour_resq_lang', lang);
    updateLanguageUI(lang);
    loadTranslations(lang);
};
function updateLanguageUI(lang) {
    document.documentElement.lang = lang;
    document.documentElement.setAttribute('data-lang', lang);
}

// ── 1. ONBOARDING & PERMISSIONS ──────────────────────────────
window.startJourney = async function() {
    if (navigator.vibrate) try { navigator.vibrate(30); } catch(e){}
    const btn = document.getElementById('btn-start-perms');
    btn.innerHTML = "LOCATING...";
    btn.disabled = true;
    
    if (!navigator.geolocation) {
        await doLocationReveal(); // Fallback
        return;
    }

    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            if (navigator.vibrate) try { navigator.vibrate([50, 50]); } catch(e){}
            userLocation.lat = pos.coords.latitude;
            userLocation.lng = pos.coords.longitude;
            setTimeout(doLocationReveal, 600);
        },
        async (err) => {
            console.warn("GPS failed, using fallback.", err);
            await doLocationReveal();
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
    );
};

async function doLocationReveal() {
    switchTab('tab-location-reveal');
    const nameEl = document.getElementById('reveal-location-name');
    
    // Reverse Geocoding with Nominatim API (OpenStreetMap)
    try {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${userLocation.lat}&lon=${userLocation.lng}&format=json`);
        const data = await res.json();
        let placeName = data.address.amenity || data.address.restaurant || data.address.road || data.address.city || "Unknown Location";
        userLocation.name = placeName;
    } catch(e) {
        userLocation.name = "Hanoi (Fallback)";
    }
    
    if (globalMap) {
        globalMap.flyTo([userLocation.lat, userLocation.lng], 18, { animate: true, duration: 2 });
    }
    
    setTimeout(() => {
        nameEl.innerText = userLocation.name;
        nameEl.style.opacity = 1;
        if (navigator.vibrate) navigator.vibrate([50, 100, 50]);
    }, 1500);
    
    setTimeout(() => {
        document.getElementById('dash-location-name').innerText = userLocation.name;
        document.getElementById('sos-address').innerText = userLocation.name;
        document.getElementById('sos-coords').innerText = `${userLocation.lat.toFixed(4)}° N, ${userLocation.lng.toFixed(4)}° E`;
        document.getElementById('global-sos-btn').classList.remove('hidden');
        switchTab('tab-dashboard');
    }, 4500);
}

// ── 2. TAB NAVIGATION ─────────────────────────────────────────
window.switchTab = function(tabId) {
    if (navigator.vibrate) navigator.vibrate(20);
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
};

// ── 3. CAMERA SCANNER (Live Video) ─────────────────────────────
window.startCameraScan = async function() {
    switchTab('tab-scanner');
    const video = document.getElementById('live-camera');
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        video.srcObject = cameraStream;
    } catch(e) {
        console.error("Camera access failed", e);
    }
};

window.stopCameraAndGoHome = function() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    switchTab('tab-dashboard');
};

window.captureAndAnalyze = async function() {
    if (navigator.vibrate) navigator.vibrate([50, 50, 50]);
    const video = document.getElementById('live-camera');
    const canvas = document.getElementById('camera-canvas');
    if (!video.videoWidth) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    const base64Image = canvas.toDataURL('image/jpeg', 0.6).split(',')[1];
    
    // Pause video
    video.pause();

    const scanTitle = document.getElementById('scan-alert-title');
    const scanPrice = document.getElementById('scan-alert-price');
    const scanMsg = document.getElementById('scan-alert-msg');
    const breakdown = document.getElementById('scan-breakdown');
    const overlay = document.getElementById('price-results-overlay');

    scanTitle.innerText = "ANALYZING...";
    scanPrice.innerText = "...";
    scanMsg.innerText = "Extracting items and checking regional prices...";
    breakdown.innerHTML = "";
    scanTitle.parentElement.className = "results-card high-contrast tier-caution";
    overlay.style.display = 'flex';

    try {
        const res = await fetch(API_BASE + '/api/v1/check-price-ocr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_base64: base64Image, language: currentLang, lat: userLocation.lat, lng: userLocation.lng })
        });
        
        if (res.status === 429) {
            scanTitle.innerText = "RATE LIMITED"; scanMsg.innerText = "Please wait."; return;
        }
        
        const data = await res.json();

        if (data.status === 'success' && data.result) {
            const r = data.result;
            
            // Build Breakdown HTML
            let bHtml = "<strong>Item Breakdown:</strong><br/>";
            r.items_checked.forEach(item => {
                bHtml += `- ${item.item_name}: ${item.unit_price.toLocaleString()} VND <em>(${item.tier.toUpperCase()})</em><br/>`;
            });
            breakdown.innerHTML = bHtml;

            if (r.overall_verdict === 'overpriced') {
                scanTitle.innerText = "OVERPRICED";
                scanTitle.parentElement.className = "results-card high-contrast tier-danger";
                document.getElementById('btn-contribute').style.display = 'none';
                window.evidenceBuffer.images.push(base64Image); // Save evidence
            } else if (r.overall_verdict === 'slightly_high') {
                scanTitle.innerText = "SLIGHTLY HIGH";
                scanTitle.parentElement.className = "results-card high-contrast tier-caution";
                document.getElementById('btn-contribute').style.display = 'none';
            } else {
                scanTitle.innerText = "FAIR PRICE";
                scanTitle.parentElement.className = "results-card high-contrast tier-fair";
                document.getElementById('btn-contribute').style.display = 'block';
            }
            
            window.lastScannedItems = r.items_checked;
            scanPrice.innerText = r.total_asked.toLocaleString() + " VND";
            scanMsg.innerText = r.summary;
        } else {
            scanTitle.innerText = "ERROR";
            scanMsg.innerText = data.message || "Failed to analyze image.";
        }
    } catch (err) {
        console.error(err);
        scanTitle.innerText = "NETWORK ERROR";
    }
};

window.closePriceResults = function() {
    if (navigator.vibrate) navigator.vibrate(20);
    document.getElementById('price-results-overlay').style.display = 'none';
    const video = document.getElementById('live-camera');
    if (video) video.play(); // Resume live view
};

async function contributePrice() {
    if (!window.lastScannedItems) return;
    const btn = document.getElementById('btn-contribute');
    btn.innerHTML = "CONTRIBUTING...";
    btn.disabled = true;
    try {
        for (const item of window.lastScannedItems) {
            await fetch(API_BASE + '/api/v1/contribute-price', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    region: "hanoi", category: "food", item_name: item.item_name, item_name_vi: item.item_name_vi,
                    price_vnd: Math.round(item.unit_price), venue_type: "street", device_id: 'dev123'
                })
            });
        }
        btn.innerHTML = "THANK YOU";
        setTimeout(() => { closePriceResults(); }, 1500);
    } catch(e) {}
}

// ── 4. LIVE TRANSLATE & SMART WIDGET ───────────────────────
window.startLiveTranslate = function() {
    switchTab('tab-translate');
};
window.stopTranslateAndGoHome = function() {
    concludeNegotiation();
    setTimeout(() => { switchTab('tab-dashboard'); }, 500); // Give time for conclude to fire
};

let vendorMicActive = false; let touristMicActive = false;
let vendorRecognition = null; let touristRecognition = null;
let liveSessionId = null;

async function ensureLiveSession() {
    if (!liveSessionId) {
        try {
            const res = await fetch(API_BASE + '/api/v1/live/start', { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') liveSessionId = data.session_id;
        } catch(e) {}
    }
}

function showSmartWidget(title, msg, isScam) {
    const w = document.getElementById('smart-ai-widget');
    const t = document.getElementById('smart-ai-title');
    const m = document.getElementById('smart-ai-msg');
    
    t.innerText = title; m.innerText = msg;
    if (isScam) {
        w.style.borderColor = 'var(--danger-red)';
        t.style.color = 'var(--danger-red)';
    } else {
        w.style.borderColor = 'var(--neon-green)';
        t.style.color = 'var(--neon-green)';
    }
    
    w.style.display = 'block';
    if (navigator.vibrate) navigator.vibrate([30,30]);
    setTimeout(() => { w.style.display = 'none'; }, 6000);
}

if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

    vendorRecognition = new SR(); vendorRecognition.lang = 'vi-VN'; vendorRecognition.continuous = false;
    vendorRecognition.onresult = async function(ev) {
        const text = ev.results[0][0].transcript;
        document.getElementById('vendor-text').textContent = text;
        window.evidenceBuffer.transcripts.push(`Vendor: ${text}`);
        await handleMessage(text, 'vi', currentLang, 'vendor', 'tourist-text');
        toggleVendorMic();
    };

    touristRecognition = new SR(); touristRecognition.lang = currentLang === 'ko' ? 'ko-KR' : currentLang === 'zh' ? 'zh-CN' : 'en-US';
    touristRecognition.continuous = false;
    touristRecognition.onresult = async function(ev) {
        const text = ev.results[0][0].transcript;
        document.getElementById('tourist-text').textContent = text;
        window.evidenceBuffer.transcripts.push(`Tourist: ${text}`);
        await handleMessage(text, currentLang, 'vi', 'tourist', 'vendor-text');
        toggleTouristMic();
    };
}

async function handleMessage(text, src, tgt, speaker, tgtEl) {
    await ensureLiveSession();
    try {
        const res = await fetch(API_BASE + '/api/v1/live/message', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: liveSessionId, text, source_lang: src, target_lang: tgt, speaker })
        });
        const data = await res.json();
        if (data.translated) document.getElementById(tgtEl).textContent = data.translated;
        
        // Smart AI Widget Triggers
        if (data.is_suspicious) {
            showSmartWidget("⚠️ WARNING", "Suspicious coercion or scam words detected. Be careful.", true);
        } else if (data.is_price_discussion) {
            showSmartWidget("💰 PRICE DETECTED", "Negotiating prices. Remember to verify with the Scan Bill feature.", false);
        }
    } catch(e) {}
}

window.toggleVendorMic = function() {
    const btn = document.querySelector('.mic-vendor');
    vendorMicActive = !vendorMicActive;
    if (vendorMicActive) {
        btn.style.background = 'white'; btn.style.color = 'black';
        if (touristMicActive) toggleTouristMic();
        if (vendorRecognition) { try { vendorRecognition.start(); } catch(e) {} }
    } else {
        btn.style.background = 'transparent'; btn.style.color = 'white';
        if (vendorRecognition) { try { vendorRecognition.stop(); } catch(e) {} }
    }
}
window.toggleTouristMic = function() {
    const btn = document.querySelector('.mic-tourist');
    touristMicActive = !touristMicActive;
    if (touristMicActive) {
        btn.style.background = 'white'; btn.style.color = 'black';
        if (vendorMicActive) toggleVendorMic();
        if (touristRecognition) { try { touristRecognition.start(); } catch(e) {} }
    } else {
        btn.style.background = 'transparent'; btn.style.color = 'white';
        if (touristRecognition) { try { touristRecognition.stop(); } catch(e) {} }
    }
}
async function concludeNegotiation() {
    if (!liveSessionId) return;
    try {
        await fetch(API_BASE + '/api/v1/live/conclude', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: liveSessionId, tourist_lang: currentLang })
        });
        liveSessionId = null;
    } catch(e) {}
}

// ── 5. GUARDIAN (Text Scam Analyze) ───────────────────────
window.toggleGuardian = function() {
    const btn = document.getElementById('guardian-mic');
    btn.classList.toggle('listening');
    if (btn.classList.contains('listening')) {
        document.getElementById('guardian-status-text').innerText = "LISTENING...";
    } else {
        document.getElementById('guardian-status-text').innerText = "TAP TO LISTEN";
    }
};

window.analyzeScam = async function() {
    const text = document.getElementById('incident-input').value;
    if (!text) return;
    const overlay = document.getElementById('scam-results-overlay');
    overlay.style.display = 'flex';
    document.getElementById('guardian-alert-title').innerText = "AI ANALYSIS";
    document.getElementById('guardian-alert-msg').innerText = "Based on your description, this might be a scam. Be careful.";
};
window.closeScamResults = function() { document.getElementById('scam-results-overlay').style.display = 'none'; };


// ── 6. SOS (Slide to SOS) ──────────────────────────────────
function initSlideToSOS() {
    const knob = document.getElementById('sos-knob');
    const track = document.getElementById('sos-track');
    if (!knob || !track) return;

    let isDragging = false, startX = 0, currentX = 0, triggered = false;
    const maxDragX = track.clientWidth - knob.clientWidth - 8;

    function startDrag(e) { if (triggered) return; isDragging = true; startX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX; knob.style.transition = 'none'; }
    function doDrag(e) {
        if (!isDragging || triggered) return;
        const clientX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX;
        currentX = Math.max(0, Math.min(clientX - startX, maxDragX));
        knob.style.transform = `translateX(${currentX}px)`;
        if (currentX >= maxDragX * 0.95 && !triggered) triggerSOS();
    }
    function endDrag() {
        if (!isDragging) return;
        isDragging = false;
        if (!triggered) { knob.style.transition = 'transform 0.3s var(--spring)'; knob.style.transform = 'translateX(0)'; }
    }

    knob.addEventListener('touchstart', startDrag, {passive: true}); window.addEventListener('touchmove', doDrag, {passive: true}); window.addEventListener('touchend', endDrag);
    knob.addEventListener('mousedown', startDrag); window.addEventListener('mousemove', doDrag); window.addEventListener('mouseup', endDrag);

    async function triggerSOS() {
        triggered = true;
        knob.style.transform = `translateX(${maxDragX}px)`; knob.style.backgroundColor = '#00FF66';
        if (navigator.vibrate) navigator.vibrate([100, 50, 100, 50, 300, 100, 300]);

        const statusEl = document.getElementById('sos-dispatch-status');
        statusEl.innerHTML = "DISPATCHING SOS WITH EVIDENCE...";

        try {
            // Sending Evidence Buffer (logs and images) along with SOS
            const payload = {
                latitude: userLocation.lat, longitude: userLocation.lng, location_name: userLocation.name,
                incident_type: "emergency", language: currentLang, severity: "critical",
                evidence: window.evidenceBuffer // Attach accumulated evidence
            };

            const res = await fetch(API_BASE + '/api/v1/sos', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            statusEl.innerHTML = `SOS SENT. EVIDENCE ATTACHED. Location shared. Call 113 NOW.`;
            window.evidenceBuffer = { images: [], transcripts: [] }; // Clear buffer after sending
        } catch(e) {
            statusEl.innerHTML = "SOS API FAILED. CALL 113 DIRECTLY.";
        }
        setTimeout(() => {
            triggered = false; knob.style.transition = 'transform 0.5s ease'; knob.style.transform = 'translateX(0)';
            knob.style.backgroundColor = 'var(--danger-red)'; statusEl.innerHTML = "";
        }, 5000);
    }
}
