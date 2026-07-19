/**
 * Tour-resQ Frontend -- Premium Flow
 * Real API Integration with new Permission & Location Reveal flow.
 */

// Configuration
const API_BASE = window.__TOUR_RESQ_API_BASE || window.location.origin;
let currentLang = localStorage.getItem('tour_resq_lang') || document.documentElement.getAttribute('data-lang') || 'en';

// Global Evidence Buffer
window.evidenceBuffer = {
    images: [], // Suspicious bills
    transcripts: [] // Conversation logs
};

let userLocation = { lat: 21.0285, lng: 105.8542, name: "Unknown Location" };
let cameraStream = null;
let sosAudioContext = null;
let sosSirenNodes = [];
let sosSirenTimer = null;
let sosSirenSweep = null;

// Handle language selection on homepage
window.changeLanguage = function(lang) {
    currentLang = lang;
    localStorage.setItem('tour_resq_lang', lang);
    document.documentElement.setAttribute('data-lang', lang);
    updateLanguageUI(lang);
    loadTranslations(lang);
    
    // Update active state on buttons
    document.querySelectorAll('.btn-lang').forEach(btn => {
        if(btn.getAttribute('data-lang') === lang) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    if (navigator.vibrate) try { navigator.vibrate(20); } catch(e){}
};

document.addEventListener('DOMContentLoaded', () => {
    initSlideToSOS();
    updateLanguageUI(currentLang);
    loadTranslations(currentLang);
    initGlobalMap();
    initRippleEffect();
    
    // Highlight initial language button
    document.querySelectorAll('.btn-lang').forEach(btn => {
        if(btn.getAttribute('data-lang') === currentLang) {
            btn.classList.add('active');
        }
    });
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
window.t = function(key, defaultVal) {
    return translations[key] || defaultVal;
};
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
    updateSpeechRecognitionLanguage();
}

// ── 1. ONBOARDING & PERMISSIONS ──────────────────────────────
window.startJourney = async function() {
    if (navigator.vibrate) try { navigator.vibrate(30); } catch(e){}
    const btn = document.getElementById('btn-start-perms');
    btn.innerHTML = "LOCATING...";
    btn.disabled = true;
    
    let resolved = false;
    const proceed = async () => {
        if (resolved) return;
        resolved = true;
        await doLocationReveal();
    };

    // Failsafe timeout (4 seconds)
    setTimeout(proceed, 4000);

    if (!navigator.geolocation) {
        return proceed();
    }

    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            if (resolved) return;
            if (navigator.vibrate) try { navigator.vibrate([50, 50]); } catch(e){}
            userLocation.lat = pos.coords.latitude;
            userLocation.lng = pos.coords.longitude;
            resolved = true;
            setTimeout(doLocationReveal, 600);
        },
        async (err) => {
            console.warn("GPS failed, using fallback.", err);
            proceed();
        },
        { enableHighAccuracy: false, timeout: 8000, maximumAge: 0 }
    );
};

async function doLocationReveal() {
    switchTab('tab-location-reveal');
    const nameEl = document.getElementById('reveal-location-name');
    
    // Reverse Geocoding with Nominatim API (OpenStreetMap)
    const reverseController = new AbortController();
    const reverseTimeout = setTimeout(() => reverseController.abort(), 1500);
    try {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${userLocation.lat}&lon=${userLocation.lng}&format=json`, {
            headers: {
                'Accept-Language': 'en'
            },
            signal: reverseController.signal
        });
        const data = await res.json();
        const address = data.address || {};
        let placeName = address.amenity || address.restaurant || address.road || address.city || "Hanoi, Vietnam";
        userLocation.name = placeName;
    } catch(e) {
        userLocation.name = "Hanoi (Fallback)";
    } finally {
        clearTimeout(reverseTimeout);
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
        document.getElementById('bottom-nav')?.classList.remove('hidden');
        switchTab('tab-dashboard');
    }, 4500);
}

// ── 2. TAB NAVIGATION ─────────────────────────────────────────
window.switchTab = function(tabId) {
    if (navigator.vibrate) try { navigator.vibrate(20); } catch(e){}
    
    // 1. Switch Tab Content
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    const target = document.getElementById(tabId);
    if (target) target.classList.add('active');
    
    // 2. Update Bottom Nav Highlight
    document.querySelectorAll('.floating-bottom-nav .nav-item').forEach(btn => btn.classList.remove('active'));
    if (tabId === 'tab-dashboard') document.getElementById('nav-home')?.classList.add('active');
    else if (tabId === 'tab-scanner') document.getElementById('nav-scan')?.classList.add('active');
    else if (tabId === 'tab-translate') document.getElementById('nav-chat')?.classList.add('active');
    else if (tabId === 'tab-sos') document.getElementById('nav-sos')?.classList.add('active');
    
    // 3. Manage Map Visibility (Only show map on SOS or Reveal)
    const mapBg = document.getElementById('global-map-bg');
    if (mapBg) {
        if (tabId === 'tab-location-reveal' || tabId === 'tab-sos') {
            mapBg.style.display = 'block';
            if (globalMap) {
                setTimeout(() => {
                    globalMap.invalidateSize();
                }, 100);
            }
        } else {
            mapBg.style.display = 'none';
        }
    }
    
    // 4. Update Feather Icons if any were dynamically added
    if (typeof feather !== 'undefined') feather.replace();
};

// Currency conversion based on language
window.formatCurrency = function(vndAmount) {
    if (!vndAmount) return "0 ₫";
    const vndStr = vndAmount.toLocaleString() + " ₫";
    let convertedStr = "";
    if (currentLang === 'en') {
        const usd = vndAmount / 25000;
        convertedStr = `(~$${usd.toFixed(2)})`;
    } else if (currentLang === 'ko') {
        const krw = vndAmount / 18;
        convertedStr = `(~${Math.round(krw).toLocaleString()} ₩)`;
    } else if (currentLang === 'zh') {
        const cny = vndAmount / 3500;
        convertedStr = `(~¥${cny.toFixed(1)})`;
    } else if (currentLang === 'ru') {
        const rub = vndAmount / 250;
        convertedStr = `(~${Math.round(rub).toLocaleString()} ₽)`;
    }
    if (convertedStr) {
        return `${vndStr} <span style="font-size: 0.85em; opacity: 0.8; font-weight: normal; margin-left: 4px;">${convertedStr}</span>`;
    }
    return vndStr;
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

// Extracted logic for analysis
async function processBase64ImageAndAnalyze(base64Image) {
    if (navigator.vibrate) navigator.vibrate([50, 50, 50]);
    
    // Pause video if playing
    const video = document.getElementById('live-camera');
    if(video) video.pause();

    const scanTitle = document.getElementById('scan-alert-title');
    const scanPrice = document.getElementById('scan-alert-price');
    const scanMsg = document.getElementById('scan-alert-msg');
    const breakdown = document.getElementById('scan-breakdown');
    const overlay = document.getElementById('price-results-overlay');

    scanTitle.innerText = t('scan.analyzing', "ANALYZING...");
    scanPrice.innerText = "...";
    scanMsg.innerText = t('price.analyzing', "Extracting items and checking regional prices...");
    breakdown.innerHTML = "";
    
    // Reset to caution style by default
    scanTitle.parentElement.classList.remove('tier-overpriced', 'tier-fair');
    scanTitle.parentElement.classList.add('tier-caution');
    
    overlay.style.display = 'flex';

    try {
        const res = await fetch(`${API_BASE}/api/v1/check-price-ocr`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image_base64: base64Image,
                language: currentLang,
                region: getRegionFromCoordinates(userLocation.lat, userLocation.lng)
            })
        });
        
        if (res.status === 429) {
            scanTitle.innerText = "RATE LIMITED"; scanMsg.innerText = "Please wait."; return;
        }
        
        const data = await res.json();
        
        if (data.status === 'success' && data.result) {
            const r = data.result;
            window.lastScannedItems = r.items_checked;
            scanPrice.innerHTML = formatCurrency(r.total_asked);
            scanMsg.innerText = r.summary;
            
            let bHtml = `<strong>${t('scan.item_breakdown', 'Item Breakdown:')}</strong><br/>`;
            r.items_checked.forEach(item => {
                const tier = item.db_tier || 'unknown';
                let priceText = formatCurrency(item.asked_price || item.unit_price);
                if (item.quantity > 1) {
                    priceText = `${item.quantity}x = ${priceText}`;
                }
                bHtml += `<div style="display:flex; justify-content:space-between; margin-bottom:4px; padding-bottom:4px; border-bottom:1px solid rgba(255,255,255,0.1)">
                    <span>${item.item_name}</span>
                    <div style="text-align:right">
                        <strong>${priceText} <em style="font-size:0.8rem;opacity:0.8;color:inherit;">(${tier.toUpperCase()})</em></strong>
                    </div>
                </div>`;
            });
            let advice = "";
            if (r.overall_verdict === 'overpriced' || r.overall_verdict === 'mixed') {
                advice = `<div style="background: rgba(239, 68, 68, 0.1); border: 1px solid var(--danger-red); padding: 10px; border-radius: 10px; margin-top: 15px; color: white;">
                    <strong style="color: var(--danger-red);">💡 ${t('scan.advice_title', 'Action Required:')}</strong><br/>
                    <span style="font-size: 0.9rem;">${t('scan.advice_overpriced', 'You are being severely overcharged. Do NOT pay the asked price. Show them the normal price or threaten to call the Tourist Police (113).')}</span>
                </div>`;
            } else if (r.overall_verdict === 'slightly_high') {
                advice = `<div style="background: rgba(245, 158, 11, 0.1); border: 1px solid #F59E0B; padding: 10px; border-radius: 10px; margin-top: 15px; color: white;">
                    <strong style="color: #F59E0B;">💡 ${t('scan.advice_title', 'Action Required:')}</strong><br/>
                    <span style="font-size: 0.9rem;">${t('scan.advice_slightly_high', 'This is a tourist premium price. Try to negotiate down by 20-30%.')}</span>
                </div>`;
            } else if (r.overall_verdict === 'insufficient_data') {
                advice = `<div style="background: rgba(100, 116, 139, 0.1); border: 1px solid #64748B; padding: 10px; border-radius: 10px; margin-top: 15px; color: white;">
                    <strong style="color: #94A3B8;">ℹ️ ${t('scan.advice_unknown', 'Unknown Price:')}</strong><br/>
                    <span style="font-size: 0.9rem;">${t('scan.advice_unknown_desc', 'Not enough data in this region to verify the price. Please use your best judgment.')}</span>
                </div>`;
            } else {
                advice = `<div style="background: rgba(57, 255, 20, 0.1); border: 1px solid var(--neon-green); padding: 10px; border-radius: 10px; margin-top: 15px; color: white;">
                    <strong style="color: var(--neon-green);">✅ ${t('scan.advice_fair', 'Safe to Pay:')}</strong><br/>
                    <span style="font-size: 0.9rem;">${t('scan.advice_fair_desc', 'This matches the local price. You can pay with confidence.')}</span>
                </div>`;
            }
            breakdown.innerHTML = bHtml + advice;
            if (r.overall_verdict === 'overpriced' || r.overall_verdict === 'mixed') {
                scanTitle.innerText = t('scan.overpriced', "OVERPRICED");
                scanTitle.parentElement.classList.remove('tier-caution', 'tier-fair', 'tier-unknown');
                scanTitle.parentElement.classList.add('tier-danger');
                document.getElementById('btn-contribute').style.display = 'none';
                document.getElementById('btn-retry').style.display = 'none';
                if (navigator.vibrate) try { navigator.vibrate([100, 50, 100, 50, 200]); } catch(e){}
            } else if (r.overall_verdict === 'slightly_high') {
                scanTitle.innerText = t('scan.slightly_high', "SLIGHTLY HIGH");
                scanTitle.parentElement.classList.remove('tier-danger', 'tier-fair', 'tier-unknown');
                scanTitle.parentElement.classList.add('tier-caution');
                document.getElementById('btn-contribute').style.display = 'none';
                document.getElementById('btn-retry').style.display = 'none';
                if (navigator.vibrate) try { navigator.vibrate([100, 50, 100]); } catch(e){}
            } else if (r.overall_verdict === 'insufficient_data') {
                scanTitle.innerText = t('scan.unknown', "UNKNOWN");
                scanTitle.parentElement.classList.remove('tier-danger', 'tier-fair', 'tier-caution');
                scanTitle.parentElement.classList.add('tier-unknown');
                document.getElementById('btn-contribute').style.display = 'none';
                document.getElementById('btn-retry').style.display = 'block';
            } else {
                scanTitle.innerText = t('scan.fair', "FAIR PRICE");
                scanTitle.parentElement.classList.remove('tier-caution', 'tier-danger', 'tier-unknown');
                scanTitle.parentElement.classList.add('tier-fair');
                document.getElementById('btn-contribute').style.display = 'block';
                document.getElementById('btn-retry').style.display = 'none';
                if (navigator.vibrate) try { navigator.vibrate([50, 50]); } catch(e){}
            }
        } else {
            scanTitle.innerText = t('scan.error', "ERROR");
            scanMsg.innerText = data.message || "Failed to analyze image.";
            document.getElementById('btn-contribute').style.display = 'none';
            document.getElementById('btn-retry').style.display = 'block';
        }
    } catch(e) {
        scanTitle.innerText = t('scan.error', "NETWORK ERROR");
        scanMsg.innerText = "Ensure backend is running and reachable.";
        document.getElementById('btn-contribute').style.display = 'none';
        document.getElementById('btn-retry').style.display = 'block';
    }
}

window.captureAndAnalyze = async function() {
    const video = document.getElementById('live-camera');
    const canvas = document.getElementById('camera-canvas');
    if (!video.videoWidth) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    const base64Image = canvas.toDataURL('image/jpeg', 0.6).split(',')[1];
    await processBase64ImageAndAnalyze(base64Image);
};

window.triggerBillUpload = function() {
    const input = document.getElementById('bill-upload');
    if (input) input.click();
};

window.handleBillUpload = function(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Show overlay immediately so user knows it's loading
    const overlay = document.getElementById('price-results-overlay');
    if (overlay) overlay.style.display = 'flex';
    const scanTitle = document.getElementById('scan-alert-title');
    if (scanTitle) scanTitle.innerText = "PROCESSING IMAGE...";
    
    const reader = new FileReader();
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            try {
                const canvas = document.getElementById('camera-canvas');
                // Downscale image if too large (prevent mobile crash)
                const MAX_WIDTH = 1200;
                let width = img.width;
                let height = img.height;
                
                if (width > MAX_WIDTH) {
                    height = Math.round((height * MAX_WIDTH) / width);
                    width = MAX_WIDTH;
                }
                
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                
                const base64Image = canvas.toDataURL('image/jpeg', 0.6).split(',')[1];
                processBase64ImageAndAnalyze(base64Image);
            } catch (err) {
                if (scanTitle) scanTitle.innerText = "IMAGE ERROR";
                console.error(err);
            }
        };
        img.onerror = function() {
            if (scanTitle) scanTitle.innerText = "INVALID IMAGE";
        };
        img.src = e.target.result;
    };
    reader.onerror = function() {
        alert('Could not read this file.');
    };
    reader.readAsDataURL(file);
    event.target.value = ""; // Reset input
};


window.closePriceResults = function() {
    try { if (navigator.vibrate) navigator.vibrate(20); } catch(e) {}
    const overlay = document.getElementById('price-results-overlay');
    if (overlay) overlay.style.display = 'none';
    
    // Attempt to resume video if it exists and has a stream
    try {
        const video = document.getElementById('live-camera');
        if (video && video.srcObject) video.play();
    } catch(e) {}
};

window.retryUpload = function() {
    closePriceResults();
    setTimeout(() => {
        const input = document.getElementById('bill-upload');
        if (input) input.click();
    }, 300); // Wait for overlay to close
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
                    region: getRegionFromCoordinates(userLocation.lat, userLocation.lng), category: "food", item_name: item.item_name, item_name_vi: item.item_name_vi,
                    price_vnd: Math.round(item.unit_price), venue_type: "street"
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
let lastPriceWarningAt = 0;

function getTouristSpeechLang() {
    return currentLang === 'ko' ? 'ko-KR' : currentLang === 'zh' ? 'zh-CN' : currentLang === 'ru' ? 'ru-RU' : 'en-US';
}

function updateSpeechRecognitionLanguage() {
    if (touristRecognition) touristRecognition.lang = getTouristSpeechLang();
    const touristLangTag = document.getElementById('tourist-lang-tag');
    if (touristLangTag) {
        const labels = { en: 'English', ko: '한국어', zh: '中文', ru: 'Русский' };
        touristLangTag.innerHTML = `<i data-feather="globe"></i> ${labels[currentLang] || 'English'}`;
        if (window.feather) feather.replace();
    }
}

async function ensureLiveSession() {
    if (!liveSessionId) {
        try {
            const res = await fetch(API_BASE + '/api/v1/live/start', { method: 'POST' });
            if (!res.ok) throw new Error(`Session API failed (${res.status})`);
            const data = await res.json();
            if (data.status === 'success') liveSessionId = data.session_id;
        } catch(e) {
            showSmartWidget("TRANSLATION ERROR", e.message || "Could not start live translation session.", true);
        }
    }
}

function showSmartWidget(title, msg, isScam) {
    const w = document.getElementById('smart-ai-widget');
    const t = document.getElementById('widget-title');
    const m = document.getElementById('widget-msg');
    if (!w || !t || !m) return;
    
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
    vendorRecognition.onerror = function(ev) {
        vendorMicActive = false;
        const btn = document.querySelector('.mic-vendor');
        if (btn) { btn.style.background = 'transparent'; btn.style.color = 'white'; }
        showSmartWidget("MIC ERROR", ev.error || "Could not hear Vietnamese speech. Try the text box.", true);
    };

    touristRecognition = new SR(); touristRecognition.lang = getTouristSpeechLang();
    touristRecognition.continuous = false;
    touristRecognition.onresult = async function(ev) {
        const text = ev.results[0][0].transcript;
        document.getElementById('tourist-text').textContent = text;
        window.evidenceBuffer.transcripts.push(`Tourist: ${text}`);
        await handleMessage(text, currentLang, 'vi', 'tourist', 'vendor-text');
        toggleTouristMic();
    };
    touristRecognition.onerror = function(ev) {
        touristMicActive = false;
        const btn = document.querySelector('.mic-tourist');
        if (btn) { btn.style.background = 'transparent'; btn.style.color = 'white'; }
        showSmartWidget("MIC ERROR", ev.error || "Could not hear tourist speech. Try the text box.", true);
    };
} else {
    document.addEventListener('DOMContentLoaded', () => {
        showSmartWidget("TEXT MODE", "Speech recognition is unavailable in this browser. Use the text boxes.", false);
    });
}

async function handleMessage(text, src, tgt, speaker, tgtEl) {
    await ensureLiveSession();
    if (!liveSessionId) return;
    try {
        const res = await fetch(API_BASE + '/api/v1/live/message', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: liveSessionId,
                text,
                source_lang: src,
                target_lang: tgt,
                speaker,
                region: getRegionFromCoordinates(userLocation.lat, userLocation.lng)
            })
        });
        if (!res.ok) throw new Error(`Live API failed (${res.status})`);
        const data = await res.json();
        if (data.translation_error) {
            showSmartWidget("TRANSLATION ERROR", data.translation_error, true);
        }
        if (data.translated) {
            document.getElementById(tgtEl).textContent = data.translated;
            if (window.speechSynthesis) {
                const utterance = new SpeechSynthesisUtterance(data.translated);
                utterance.lang = tgt === 'vi' ? 'vi-VN' : tgt === 'ko' ? 'ko-KR' : tgt === 'zh' ? 'zh-CN' : 'en-US';
                window.speechSynthesis.speak(utterance);
            }
        } else {
            showSmartWidget("TRANSLATION EMPTY", "The provider returned no translation.", true);
        }
        
        // Smart AI Widget Triggers
        if (data.price_alert?.should_alert) {
            const isHighRisk = data.price_alert.tier === 'overpriced';
            lastPriceWarningAt = Date.now();
            showSmartWidget("PRICE WARNING", data.price_alert.message, isHighRisk);
        } else if (data.is_suspicious) {
            showSmartWidget("⚠️ WARNING", "Suspicious coercion or scam words detected. Be careful.", true);
        } else if (data.is_price_discussion) {
            showSmartWidget("💰 PRICE DETECTED", "Negotiating prices. Remember to verify with the Scan Bill feature.", false);
        }
        if (data.analysis_status === 'queued') {
            setTimeout(() => refreshLiveInsights(liveSessionId), 900);
            setTimeout(() => refreshLiveInsights(liveSessionId), 1800);
        }
    } catch(e) {
        showSmartWidget("TRANSLATION ERROR", e.message || "Could not reach the translation service.", true);
    }
}

window.sendManualLiveMessage = async function(speaker) {
    const isTourist = speaker === 'tourist';
    const input = document.getElementById(isTourist ? 'tourist-manual-input' : 'vendor-manual-input');
    const text = input?.value?.trim();
    if (!text) return;

    if (isTourist) {
        document.getElementById('tourist-text').textContent = text;
        window.evidenceBuffer.transcripts.push(`Tourist: ${text}`);
        input.value = '';
        await handleMessage(text, currentLang, 'vi', 'tourist', 'vendor-text');
    } else {
        document.getElementById('vendor-text').textContent = text;
        window.evidenceBuffer.transcripts.push(`Vendor: ${text}`);
        input.value = '';
        await handleMessage(text, 'vi', currentLang, 'vendor', 'tourist-text');
    }
};

async function refreshLiveInsights(sessionId) {
    if (!sessionId) return;
    try {
        const res = await fetch(API_BASE + `/api/v1/live/insights/${sessionId}?limit=3`);
        const data = await res.json();
        if (data.status !== 'success' || !data.observations?.length) return;

        const latest = data.observations[0];
        const warningIsFresh = Date.now() - lastPriceWarningAt < 6000;
        if (latest.should_alert) {
            showSmartWidget("WARNING", latest.summary || "Potential tourist risk detected.", true);
        } else if (latest.price_vnd > 0 && !warningIsFresh) {
            const item = latest.item_name || "item";
            showSmartWidget("PRICE CAPTURED", `${item}: ${latest.price_vnd.toLocaleString()} VND`, false);
        }
    } catch(e) {}
}

window.toggleVendorMic = function() {
    const btn = document.querySelector('.mic-vendor');
    if (!vendorRecognition) {
        showSmartWidget("TEXT MODE", "Speech recognition is unavailable in this browser. Use the vendor text box.", false);
        return;
    }
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
    if (!touristRecognition) {
        showSmartWidget("TEXT MODE", "Speech recognition is unavailable in this browser. Use the tourist text box.", false);
        return;
    }
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
    document.getElementById('guardian-alert-title').innerText = "ANALYZING...";
    document.getElementById('guardian-alert-msg').innerText = "Please wait, AI is analyzing the situation...";
    
    try {
        const region = getRegionFromCoordinates(userLocation.lat, userLocation.lng);
        const res = await fetch(API_BASE + '/api/v1/analyze-situation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                description: text,
                language: currentLang,
                location: region,
                lat: userLocation.lat,
                lng: userLocation.lng
            })
        });
        const data = await res.json();
        
        if (data.status === 'success' && data.scam_assessment) {
            const scam = data.scam_assessment;
            document.getElementById('guardian-alert-title').innerText = scam.detected ? "SCAM DETECTED" : "AI ANALYSIS";
            document.getElementById('guardian-alert-msg').innerText = scam.ai_analysis || scam.advice?.join('\n') || "Be careful with your belongings and negotiate clearly.";
        } else {
            document.getElementById('guardian-alert-title').innerText = "ERROR";
            document.getElementById('guardian-alert-msg').innerText = "Could not analyze the situation.";
        }
    } catch(e) {
        document.getElementById('guardian-alert-title').innerText = "ERROR";
        document.getElementById('guardian-alert-msg').innerText = "Network Error.";
    }
};
window.closeScamResults = function() { document.getElementById('scam-results-overlay').style.display = 'none'; };


// ── 6. SOS (Slide to SOS) ──────────────────────────────────
function stopSOSSiren() {
    if (sosSirenTimer) {
        clearTimeout(sosSirenTimer);
        sosSirenTimer = null;
    }
    if (sosSirenSweep) {
        clearInterval(sosSirenSweep);
        sosSirenSweep = null;
    }
    sosSirenNodes.forEach(node => {
        try {
            if (node.stop) node.stop();
            if (node.disconnect) node.disconnect();
        } catch(e) {}
    });
    sosSirenNodes = [];
    document.body?.classList.remove('sos-siren-active');
}

function startSOSSiren() {
    try {
        stopSOSSiren();
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextClass) return;

        sosAudioContext = sosAudioContext || new AudioContextClass();
        if (sosAudioContext.state === 'suspended') sosAudioContext.resume();

        const now = sosAudioContext.currentTime;
        const sosMasterGain = sosAudioContext.createGain();
        const sirenGain = sosAudioContext.createGain();
        const compressor = sosAudioContext.createDynamicsCompressor();
        const oscillatorHigh = sosAudioContext.createOscillator();
        const oscillatorLow = sosAudioContext.createOscillator();

        sosMasterGain.gain.setValueAtTime(0.95, now);
        sirenGain.gain.setValueAtTime(0.0001, now);
        sirenGain.gain.exponentialRampToValueAtTime(0.85, now + 0.08);

        compressor.threshold.setValueAtTime(-18, now);
        compressor.knee.setValueAtTime(20, now);
        compressor.ratio.setValueAtTime(8, now);
        compressor.attack.setValueAtTime(0.003, now);
        compressor.release.setValueAtTime(0.18, now);

        oscillatorHigh.type = 'square';
        oscillatorLow.type = 'sawtooth';
        oscillatorHigh.frequency.setValueAtTime(880, now);
        oscillatorLow.frequency.setValueAtTime(440, now);

        oscillatorHigh.connect(sirenGain);
        oscillatorLow.connect(sirenGain);
        sirenGain.connect(compressor);
        compressor.connect(sosMasterGain);
        sosMasterGain.connect(sosAudioContext.destination);

        oscillatorHigh.start(now);
        oscillatorLow.start(now);
        sosSirenNodes = [oscillatorHigh, oscillatorLow, sirenGain, compressor, sosMasterGain];
        document.body?.classList.add('sos-siren-active');

        let high = false;
        sosSirenSweep = setInterval(() => {
            high = !high;
            const t = sosAudioContext.currentTime;
            oscillatorHigh.frequency.cancelScheduledValues(t);
            oscillatorLow.frequency.cancelScheduledValues(t);
            oscillatorHigh.frequency.linearRampToValueAtTime(high ? 1320 : 760, t + 0.22);
            oscillatorLow.frequency.linearRampToValueAtTime(high ? 660 : 380, t + 0.22);
            if (navigator.vibrate) {
                try { navigator.vibrate([80, 40, 80]); } catch(e) {}
            }
        }, 420);

        sosSirenTimer = setTimeout(stopSOSSiren, 12000);
    } catch(e) {
        console.warn("SOS siren failed", e);
    }
}

function initSlideToSOS() {
    const knob = document.getElementById('sos-knob');
    const track = document.getElementById('sos-track');
    if (!knob || !track) return;

    let isDragging = false, startX = 0, currentX = 0, triggered = false;
    const getMaxDragX = () => track.clientWidth - knob.clientWidth - 8;

    function startDrag(e) { if (triggered) return; isDragging = true; startX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX; knob.style.transition = 'none'; }
    function doDrag(e) {
        if (!isDragging || triggered) return;
        const clientX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX;
        const maxDragX = getMaxDragX();
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
        const maxDragX = getMaxDragX();
        knob.style.transform = `translateX(${maxDragX}px)`; knob.style.backgroundColor = '#00FF66';
        if (navigator.vibrate) navigator.vibrate([100, 50, 100, 50, 300, 100, 300]);
        startSOSSiren();

        const panel = document.getElementById('sos-active-panel');
        if (panel) panel.style.display = 'block';

        try {
            const payload = {
                latitude: userLocation.lat,
                longitude: userLocation.lng,
                incident_type: "emergency",
                description: window.evidenceBuffer.transcripts.join('\n'),
                language: currentLang,
                severity: "critical",
                photo_base64: window.evidenceBuffer.images[0] || ""
            };

            const res = await fetch(API_BASE + '/api/v1/sos', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            await res.json();
            if (panel) panel.querySelector('p').innerText = "Location shared. Call 113 now.";
            window.evidenceBuffer = { images: [], transcripts: [] }; // Clear buffer after sending
        } catch(e) {
            if (panel) panel.querySelector('p').innerText = "SOS API failed. Call 113 directly.";
        }
        setTimeout(() => {
            triggered = false; knob.style.transition = 'transform 0.5s ease'; knob.style.transform = 'translateX(0)';
            knob.style.backgroundColor = 'var(--danger-red)';
        }, 5000);
    }
}

// ── 7. UTILS & REPORTING ──────────────────────────────────
function getRegionFromCoordinates(lat, lng) {
    if (lat > 20.5 && lat < 21.5 && lng > 105.0 && lng < 106.5) return 'hanoi';
    if (lat > 15.5 && lat < 16.5 && lng > 107.5 && lng < 108.5) return 'danang';
    if (lat > 10.0 && lat < 11.0 && lng > 106.0 && lng < 107.0) return 'hcmc';
    if (lat > 15.0 && lat < 16.0 && lng > 108.0 && lng < 108.5) return 'hoian';
    if (lat > 12.0 && lat < 12.5 && lng > 109.0 && lng < 109.5) return 'nhatrang';
    if (lat > 10.0 && lat < 10.5 && lng > 103.5 && lng < 104.5) return 'phuquoc';
    return 'hanoi'; // Default
}

window.dispatchReport = async function() {
    if (navigator.vibrate) navigator.vibrate(100);
    const btn = document.querySelector('#sos-active-panel .btn-danger');
    if (btn) { btn.innerHTML = "SENDING..."; btn.disabled = true; }
    
    try {
        await fetch(API_BASE + '/api/v1/dispatch-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: userLocation.lat,
                lng: userLocation.lng,
                scam_type: "scam_report",
                details: window.evidenceBuffer.transcripts.join('\n') || `Emergency report from ${userLocation.name}`,
                authority_name: "Tourist Police"
            })
        });
        if (btn) { btn.innerHTML = "SENT TO POLICE"; btn.style.background = 'var(--neon-green)'; btn.style.color = 'black'; }
        window.evidenceBuffer = { images: [], transcripts: [] };
    } catch(e) {
        if (btn) { btn.innerHTML = "FAILED. TRY SOS."; }
    }
};

window.cancelSOS = function() {
    const panel = document.getElementById('sos-active-panel');
    const knob = document.getElementById('sos-knob');
    stopSOSSiren();
    if (panel) panel.style.display = 'none';
    if (knob) {
        knob.style.transition = 'transform 0.3s ease';
        knob.style.transform = 'translateX(0)';
        knob.style.backgroundColor = '';
    }
};
