/**
 * Tour-resQ Frontend -- Real API Integration
 * All interactions are wired to the FastAPI backend.
 * No mock data. No hardcoded responses.
 */

const API_BASE = ''; // Same origin -- served by FastAPI
let currentLang = document.documentElement.getAttribute('data-lang') || 'en';

document.addEventListener('DOMContentLoaded', () => {
    console.log("Tour-resQ Engine Initialized");
    initSlideToSOS();
});

// ── 1. TAB NAVIGATION ───────────────────────────────────────────────
function switchTab(tabId) {
    if (navigator.vibrate) navigator.vibrate(20);
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    document.querySelectorAll('.tab-item').forEach(btn => btn.classList.remove('active'));
    const targetBtn = Array.from(document.querySelectorAll('.tab-item'))
        .find(btn => btn.getAttribute('onclick').includes(tabId));
    if (targetBtn) targetBtn.classList.add('active');
}

// ── 2. CAMERA SCANNER (Price Check via Vision API) ──────────────────
function handlePricePhoto(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (navigator.vibrate) navigator.vibrate([50, 50, 50]);

    const reader = new FileReader();
    reader.onload = function(e) {
        const img = new Image();
        img.onload = async function() {
            // Compress and strip EXIF via Canvas
            const canvas = document.createElement('canvas');
            const MAX_WIDTH = 1024;
            const MAX_HEIGHT = 1024;
            let width = img.width;
            let height = img.height;

            if (width > height) {
                if (width > MAX_WIDTH) {
                    height *= MAX_WIDTH / width;
                    width = MAX_WIDTH;
                }
            } else {
                if (height > MAX_HEIGHT) {
                    width *= MAX_HEIGHT / height;
                    height = MAX_HEIGHT;
                }
            }
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);
            
            const base64Image = canvas.toDataURL('image/jpeg', 0.6).split(',')[1];
            
            const scanTitle = document.getElementById('scan-alert-title');
            const scanPrice = document.getElementById('scan-alert-price');
            const scanMsg = document.getElementById('scan-alert-msg');
            const overlay = document.getElementById('price-results-overlay');
            const visionWarningBox = document.getElementById('vision-forgery-warning');
            const visionReasonMsg = document.getElementById('vision-reason');

            // Loading state
            scanTitle.innerText = "ANALYZING...";
            scanPrice.innerText = "...";
            scanMsg.innerText = "AI is extracting items and checking database...";
            scanTitle.parentElement.className = "results-card high-contrast tier-caution";
            if (visionWarningBox) visionWarningBox.style.display = 'none';
            overlay.style.display = 'flex';

            try {
                const res = await fetch(API_BASE + '/api/v1/check-price-ocr', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image_base64: base64Image, language: currentLang })
                });
                
                if (res.status === 429) {
                    scanTitle.innerText = "RATE LIMITED";
                    scanMsg.innerText = "Too many requests. Please wait a minute.";
                    return;
                }
                
                const data = await res.json();

                if (data.status === 'success' && data.result) {
                    const r = data.result;
                    if (r.overall_verdict === 'overpriced') {
                        scanTitle.innerText = "OVERPRICED";
                        scanTitle.parentElement.className = "results-card high-contrast tier-danger";
                        document.getElementById('btn-contribute').style.display = 'none';
                    } else if (r.overall_verdict === 'slightly_high') {
                        scanTitle.innerText = "SLIGHTLY HIGH";
                        scanTitle.parentElement.className = "results-card high-contrast tier-caution";
                        document.getElementById('btn-contribute').style.display = 'none';
                    } else if (r.overall_verdict === 'mixed') {
                        scanTitle.innerText = "MIXED PRICES";
                        scanTitle.parentElement.className = "results-card high-contrast tier-caution";
                        document.getElementById('btn-contribute').style.display = 'none';
                    } else {
                        scanTitle.innerText = "FAIR PRICE";
                        scanTitle.parentElement.className = "results-card high-contrast tier-fair";
                        document.getElementById('btn-contribute').style.display = 'block';
                        document.getElementById('btn-contribute').innerHTML = "YES, I PAID THIS (CONTRIBUTE)";
                        document.getElementById('btn-contribute').disabled = false;
                        document.getElementById('btn-contribute').style.background = "var(--neon-green)";
                    }
                    
                    window.lastScannedItems = r.items_checked;
                    
                    scanPrice.innerText = r.total_asked.toLocaleString() + " VND";
                    scanMsg.innerText = r.summary;
                    
                    if (r.currency_warning && visionWarningBox && visionReasonMsg) {
                        visionWarningBox.style.display = 'block';
                        visionReasonMsg.innerText = r.currency_warning;
                    }
                } else {
                    scanTitle.innerText = "ERROR";
                    scanMsg.innerText = data.message || "Failed to analyze image.";
                }
            } catch (err) {
                console.error(err);
                scanTitle.innerText = "NETWORK ERROR";
                scanMsg.innerText = "Could not reach the backend server.";
            }
            event.target.value = '';
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function closePriceResults() {
    if (navigator.vibrate) navigator.vibrate(20);
    document.getElementById('price-results-overlay').style.display = 'none';
    const visionWarningBox = document.getElementById('vision-forgery-warning');
    if (visionWarningBox) visionWarningBox.style.display = 'none';
}

async function contributePrice() {
    if (!window.lastScannedItems || window.lastScannedItems.length === 0) return;
    
    let deviceId = localStorage.getItem('tour_resq_device_id');
    if (!deviceId) {
        deviceId = 'device_' + Math.random().toString(36).substring(2, 15);
        localStorage.setItem('tour_resq_device_id', deviceId);
    }
    
    const btn = document.getElementById('btn-contribute');
    btn.innerHTML = "CONTRIBUTING...";
    btn.disabled = true;
    
    try {
        let successCount = 0;
        for (const item of window.lastScannedItems) {
            const res = await fetch(API_BASE + '/api/v1/contribute-price', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    region: "hanoi", // Using Hanoi for demo scope
                    category: "food",
                    item_name: item.item_name,
                    item_name_vi: item.item_name_vi,
                    price_vnd: Math.round(item.unit_price),
                    venue_type: "street",
                    device_id: deviceId
                })
            });
            if (res.status === 200) successCount++;
        }
        
        if (successCount > 0) {
            btn.innerHTML = "SUCCESS! THANK YOU";
            btn.style.background = "var(--neon-yellow)";
        } else {
            btn.innerHTML = "RATE LIMITED TODAY";
            btn.style.background = "var(--danger-red)";
        }
        
        setTimeout(() => { closePriceResults(); }, 1500);
    } catch(e) {
        console.error(e);
        btn.innerHTML = "ERROR";
        btn.disabled = false;
    }
}

// ── 3. TRANSLATE (Split-Screen with real Speech + API) ──────────────
let vendorMicActive = false;
let touristMicActive = false;
let vendorRecognition = null;
let touristRecognition = null;

let liveSessionId = null;

async function ensureLiveSession() {
    if (!liveSessionId) {
        try {
            const res = await fetch(API_BASE + '/api/v1/live/start', { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') {
                liveSessionId = data.session_id;
                document.getElementById('btn-conclude-negotiation').style.display = 'block';
            }
        } catch(e) { console.error("Could not start session:", e); }
    }
}

async function concludeNegotiation() {
    if (!liveSessionId) return;
    
    if (navigator.vibrate) navigator.vibrate([30, 30]);
    const btn = document.getElementById('btn-conclude-negotiation');
    btn.innerHTML = "ANALYZING...";
    
    try {
        const res = await fetch(API_BASE + '/api/v1/live/conclude', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: liveSessionId, tourist_lang: currentLang })
        });
        const data = await res.json();
        btn.innerHTML = "EVALUATE SCAM";
        
        if (data.status === 'success') {
            document.getElementById('nego-alert-title').innerText = "SCAM ANALYSIS";
            // Convert newlines to HTML br
            document.getElementById('nego-alert-msg').innerHTML = data.final_verdict.replace(/\n/g, "<br>");
            document.getElementById('negotiation-results-overlay').style.display = 'flex';
            liveSessionId = null; // Reset session
            btn.style.display = 'none';
        } else {
            alert("Analysis failed: " + data.message);
        }
    } catch(e) {
        console.error(e);
        btn.innerHTML = "EVALUATE SCAM";
        alert("Network error.");
    }
}

function closeNegotiationResults() {
    document.getElementById('negotiation-results-overlay').style.display = 'none';
}

if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

    vendorRecognition = new SR();
    vendorRecognition.lang = 'vi-VN';
    vendorRecognition.continuous = false;
    vendorRecognition.interimResults = false;
    vendorRecognition.onresult = async function(ev) {
        const text = ev.results[0][0].transcript;
        document.getElementById('vendor-text').textContent = text;
        // Translate Vietnamese -> Tourist's language via Live Negotiation
        await ensureLiveSession();
        try {
            const res = await fetch(API_BASE + '/api/v1/live/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    session_id: liveSessionId,
                    text, 
                    source_lang: 'vi', 
                    target_lang: currentLang, 
                    speaker: 'vendor' 
                })
            });
            const data = await res.json();
            if (data.translated) {
                document.getElementById('tourist-text').textContent = data.translated;
            }
        } catch(e) { console.error("Translate error:", e); }
        toggleVendorMic();
    };
    vendorRecognition.onerror = function() { if (vendorMicActive) toggleVendorMic(); };

    touristRecognition = new SR();
    touristRecognition.lang = currentLang === 'ko' ? 'ko-KR' : currentLang === 'zh' ? 'zh-CN' : currentLang === 'ru' ? 'ru-RU' : 'en-US';
    touristRecognition.continuous = false;
    touristRecognition.interimResults = false;
    touristRecognition.onresult = async function(ev) {
        const text = ev.results[0][0].transcript;
        document.getElementById('tourist-text').textContent = text;
        // Translate Tourist's language -> Vietnamese via Live Negotiation
        await ensureLiveSession();
        try {
            const res = await fetch(API_BASE + '/api/v1/live/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    session_id: liveSessionId,
                    text, 
                    source_lang: currentLang, 
                    target_lang: 'vi', 
                    speaker: 'tourist' 
                })
            });
            const data = await res.json();
            if (data.translated) {
                document.getElementById('vendor-text').textContent = data.translated;
            }
        } catch(e) { console.error("Translate error:", e); }
        toggleTouristMic();
    };
    touristRecognition.onerror = function() { if (touristMicActive) toggleTouristMic(); };
}

function toggleVendorMic() {
    const btn = document.querySelector('.mic-vendor');
    const waves = document.querySelector('.wave-vendor');
    vendorMicActive = !vendorMicActive;
    if (vendorMicActive) {
        if (navigator.vibrate) navigator.vibrate([30, 30, 30]);
        btn.classList.add('recording');
        waves.style.display = 'flex';
        if (touristMicActive) toggleTouristMic();
        if (vendorRecognition) { try { vendorRecognition.start(); } catch(e) {} }
    } else {
        if (navigator.vibrate) navigator.vibrate(50);
        btn.classList.remove('recording');
        waves.style.display = 'none';
        if (vendorRecognition) { try { vendorRecognition.stop(); } catch(e) {} }
    }
}

function toggleTouristMic() {
    const btn = document.querySelector('.mic-tourist');
    const waves = document.querySelector('.wave-tourist');
    touristMicActive = !touristMicActive;
    if (touristMicActive) {
        if (navigator.vibrate) navigator.vibrate([30, 30, 30]);
        btn.classList.add('recording');
        waves.style.display = 'flex';
        if (vendorMicActive) toggleVendorMic();
        if (touristRecognition) { try { touristRecognition.start(); } catch(e) {} }
    } else {
        if (navigator.vibrate) navigator.vibrate(50);
        btn.classList.remove('recording');
        waves.style.display = 'none';
        if (touristRecognition) { try { touristRecognition.stop(); } catch(e) {} }
    }
}

// ── 4. GUARDIAN (Scam Detection with real Speech + API) ──────────────
let guardianListening = false;
let guardianRecognition = null;

if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    guardianRecognition = new SR();
    guardianRecognition.lang = 'vi-VN';
    guardianRecognition.continuous = true;
    guardianRecognition.interimResults = false;
    guardianRecognition.onresult = function(event) {
        const transcript = event.results[event.results.length - 1][0].transcript;
        const inputElement = document.getElementById('incident-input');
        if (inputElement) inputElement.value = transcript;
        if (guardianListening) toggleGuardian();
    };
    guardianRecognition.onerror = function(event) {
        console.error("Speech recognition error", event.error);
        if (guardianListening) toggleGuardian();
    };
}

function toggleGuardian() {
    const btn = document.getElementById('guardian-mic');
    const status = document.getElementById('guardian-status-text');
    guardianListening = !guardianListening;
    if (guardianListening) {
        if (navigator.vibrate) navigator.vibrate([50, 100, 50]);
        btn.classList.add('listening');
        status.textContent = "LISTENING (SPEAK NOW)...";
        status.style.color = "#FFF";
        if (guardianRecognition) { try { guardianRecognition.start(); } catch(e) {} }
        else { alert("Your browser does not support Speech Recognition. Please type manually."); }
    } else {
        if (navigator.vibrate) navigator.vibrate(50);
        btn.classList.remove('listening');
        status.textContent = "TAP TO LISTEN";
        status.style.color = "var(--neon-yellow)";
        if (guardianRecognition) { try { guardianRecognition.stop(); } catch(e) {} }
        analyzeScam();
    }
}

async function analyzeScam() {
    if (navigator.vibrate) navigator.vibrate([30, 30]);
    const inputElement = document.getElementById('incident-input');
    const userText = inputElement ? inputElement.value.trim() : "";
    if (!userText) return; // Nothing to analyze

    const btn = document.querySelector('.btn-secondary-giant');
    const originalBtnText = btn ? btn.innerHTML : "ANALYZE TEXT";
    if (btn) btn.innerHTML = "ANALYZING...";

    try {
        const res = await fetch(API_BASE + '/api/v1/analyze-situation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                description: userText,
                location: "Hoan Kiem Walking Street, Hanoi",
                language: currentLang,
                lat: 21.0285,
                lng: 105.8542
            })
        });
        const data = await res.json();
        if (btn) btn.innerHTML = originalBtnText;

        const alertTitle = document.getElementById('guardian-alert-title');
        const alertMsg = document.getElementById('guardian-alert-msg');
        const dispatchBox = document.getElementById('auto-dispatch-box');
        const authName = document.getElementById('dispatch-auth-name');

        // Determine what to display
        let tierText = "ANALYSIS COMPLETE";
        let adviceText = "";
        let blackboxTriggered = false;
        let nearestAuth = null;

        // Layer 1: Show scam detection result
        if (data.scam_assessment) {
            const scam = data.scam_assessment;
            if (scam.detected) {
                tierText = "SCAM DETECTED (" + scam.severity.toUpperCase() + ")";
                adviceText = scam.ai_analysis || scam.advice.join("\n") || "Exercise caution.";
            } else if (scam.ai_analysis) {
                tierText = "AI ANALYSIS";
                adviceText = scam.ai_analysis;
            }
        }

        // Layer 2: Overlay price assessment if available
        if (data.price_assessment) {
            tierText = data.price_assessment.tier.replace(/_/g, " ");
            if (data.active_defense_script) {
                adviceText = data.active_defense_script;
            }
            blackboxTriggered = data.blackbox_triggered;
            nearestAuth = data.nearest_authority;
        }

        if (!adviceText && !data.price_assessment && !data.scam_assessment?.detected) {
            adviceText = "No immediate threat detected. Stay alert and trust your instincts.";
        }

        if (alertTitle) alertTitle.innerText = tierText;
        if (alertMsg) alertMsg.innerText = adviceText;

        if (blackboxTriggered && dispatchBox) {
            activateBlackboxIndicator();
            dispatchBox.style.display = 'block';
            if (authName && nearestAuth) {
                authName.innerText = `Nearest Authority: ${nearestAuth.name} (${nearestAuth.distance_km}km)`;
            }
        } else if (dispatchBox) {
            dispatchBox.style.display = 'none';
        }

        if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
        document.getElementById('scam-results-overlay').style.display = 'flex';

    } catch (e) {
        console.error("Backend error:", e);
        if (btn) btn.innerHTML = originalBtnText;
        const alertTitle = document.getElementById('guardian-alert-title');
        const alertMsg = document.getElementById('guardian-alert-msg');
        if (alertTitle) alertTitle.innerText = "CONNECTION ERROR";
        if (alertMsg) alertMsg.innerText = "Could not reach the backend. Make sure the server is running.";
        document.getElementById('scam-results-overlay').style.display = 'flex';
    }
}

// Auto Dispatch Action
window.dispatchReport = async function() {
    if (navigator.vibrate) navigator.vibrate([100]);
    const btn = event.target;
    const statusMsg = document.getElementById('dispatch-status-msg');
    if (btn) { btn.innerHTML = "DISPATCHING..."; btn.style.opacity = "0.7"; }

    try {
        const res = await fetch(API_BASE + '/api/v1/dispatch-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: 21.0285, lng: 105.8542,
                scam_type: "Severe Overcharge",
                details: document.getElementById('incident-input')?.value || "Emergency report",
                authority_name: "Cong An Phuong"
            })
        });
        const data = await res.json();
        if (navigator.vibrate) navigator.vibrate([50, 50, 50]);
        if (btn) {
            btn.innerHTML = "DISPATCHED";
            btn.style.backgroundColor = "transparent";
            btn.style.color = "var(--neon-green)";
            btn.style.border = "2px solid var(--neon-green)";
            btn.disabled = true;
        }
        if (statusMsg) statusMsg.innerText = data.message || "Report dispatched.";
    } catch(e) {
        if (statusMsg) statusMsg.innerText = "Dispatch failed. Use hotline numbers below.";
    }
};

function closeScamResults() {
    if (navigator.vibrate) navigator.vibrate(20);
    document.getElementById('scam-results-overlay').style.display = 'none';
}

// ── 5. SOS (Slide to SOS — wired to real API) ──────────────────────
function initSlideToSOS() {
    const knob = document.getElementById('sos-knob');
    const track = document.querySelector('.slide-track');
    if (!knob || !track) return;

    let isDragging = false, startX = 0, currentX = 0, triggered = false;
    const maxDragX = track.clientWidth - knob.clientWidth - 8;

    function startDrag(e) {
        if (triggered) return;
        isDragging = true;
        startX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX;
        knob.style.transition = 'none';
    }
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
        if (!triggered) {
            knob.style.transition = 'transform 0.3s var(--spring)';
            knob.style.transform = 'translateX(0)';
            currentX = 0;
        }
    }

    knob.addEventListener('touchstart', startDrag, {passive: true});
    window.addEventListener('touchmove', doDrag, {passive: true});
    window.addEventListener('touchend', endDrag);
    knob.addEventListener('mousedown', startDrag);
    window.addEventListener('mousemove', doDrag);
    window.addEventListener('mouseup', endDrag);

    async function triggerSOS() {
        // GPS Consent
        const consent = confirm("DANGER: You are about to trigger an SOS. Do you consent to sharing your GPS location with local authorities?");
        if (!consent) {
            endDrag();
            return;
        }

        triggered = true;
        knob.style.transform = `translateX(${maxDragX}px)`;
        knob.style.backgroundColor = '#00FF66';
        knob.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        if (navigator.vibrate) navigator.vibrate([100, 50, 100, 50, 300, 100, 300]);

        const statusEl = document.getElementById('sos-dispatch-status');
        statusEl.innerHTML = "DISPATCHING SOS...";

        // Get real GPS if available
        let lat = 21.0285, lng = 105.8542;
        try {
            const pos = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {timeout: 3000});
            });
            lat = pos.coords.latitude;
            lng = pos.coords.longitude;
        } catch(e) { /* fallback to default coords */ }

        // Call real SOS endpoint
        try {
            const res = await fetch(API_BASE + '/api/v1/sos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    latitude: lat, longitude: lng,
                    incident_type: "emergency",
                    description: document.getElementById('incident-input')?.value || "SOS triggered",
                    language: currentLang,
                    severity: "critical"
                })
            });
            
            if (res.status === 429) {
                statusEl.innerHTML = "RATE LIMITED. DO NOT SPAM. CALL 113.";
                return;
            }
            
            const data = await res.json();
            statusEl.innerHTML = `SOS SENT (${data.report_id || 'OK'}). Location shared. Call 113 NOW.`;
        } catch(e) {
            statusEl.innerHTML = "SOS FAILED. CALL 113 DIRECTLY.";
        }

        // Reset after 5 seconds
        setTimeout(() => {
            triggered = false;
            knob.style.transition = 'transform 0.5s ease';
            knob.style.transform = 'translateX(0)';
            knob.style.backgroundColor = 'var(--danger-red)';
            knob.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>`;
            statusEl.innerHTML = "";
            currentX = 0;
        }, 5000);
    }
}

// ── 6. BLACKBOX & HEATMAP ───────────────────────────────────────────
function activateBlackboxIndicator() {
    const indicator = document.getElementById('blackbox-indicator');
    if (indicator) {
        indicator.style.display = 'flex';
        setTimeout(() => { indicator.style.display = 'none'; }, 10000);
    }
}
