/**
 * Tour-resQ Frontend — Assistive & Safety-First Engine
 * Focuses on High-Contrast, Haptics, Slide-to-Unlock, and Split-Screen Interactions.
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log("Assistive UX Engine Initialized");
    initSlideToSOS();
});

// ── 1. TAB NAVIGATION ───────────────────────────────────────────────
function switchTab(tabId) {
    // Haptic feedback
    if (navigator.vibrate) navigator.vibrate(20);

    // Update Tab Content
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.getElementById(tabId).classList.add('active');

    // Update Tab Bar UI
    document.querySelectorAll('.tab-item').forEach(btn => {
        btn.classList.remove('active');
    });
    // Find the button that called this (or match by some data attribute)
    // Quick hack for demo: select by matching the onclick string
    const targetBtn = Array.from(document.querySelectorAll('.tab-item')).find(btn => btn.getAttribute('onclick').includes(tabId));
    if (targetBtn) targetBtn.classList.add('active');
}

// ── 2. CAMERA SCANNER (Price Check) ─────────────────────────────────
function handlePricePhoto(e) {
    const file = e.target.files[0];
    if (!file) return;

    // Heavy haptic for primary action
    if (navigator.vibrate) navigator.vibrate([50, 50, 50]);
    
    const scanTitle = document.getElementById('scan-alert-title');
    const scanPrice = document.getElementById('scan-alert-price');
    const scanMsg = document.getElementById('scan-alert-msg');
    const visionWarningBox = document.getElementById('vision-forgery-warning');
    const visionReasonMsg = document.getElementById('vision-reason');
    
    // Simulate API delay
    setTimeout(() => {
        if (navigator.vibrate) navigator.vibrate(100); // Result ready
        
        // Mock Vision response
        const mockVisionAssessment = {
            forgery_detected: true,
            risk_level: "HIGH",
            analysis_reason: "Double-Menu Detected: Layout analysis reveals two distinct columns. The English column lists prices approximately 300% higher than the Vietnamese column on the same page."
        };
        
        if (scanTitle) scanTitle.innerText = "FORGERY DETECTED";
        if (scanTitle) scanTitle.parentElement.className = "results-card high-contrast tier-overpriced";
        if (scanPrice) scanPrice.innerText = "WARNING";
        if (scanMsg) scanMsg.innerText = "Do not pay. This menu appears to be manipulated to overcharge tourists.";
        
        if (visionWarningBox && visionReasonMsg) {
            if (mockVisionAssessment.forgery_detected) {
                visionWarningBox.style.display = 'block';
                visionReasonMsg.innerText = mockVisionAssessment.analysis_reason;
            } else {
                visionWarningBox.style.display = 'none';
            }
        }
        
        // Trigger Blackbox for severe forgery
        if (typeof activateBlackboxIndicator === 'function') {
            activateBlackboxIndicator();
        }
        
        document.getElementById('price-results-overlay').style.display = 'flex';
    }, 1500);
}

function closePriceResults() {
    if (navigator.vibrate) navigator.vibrate(20);
    document.getElementById('price-results-overlay').style.display = 'none';
    const visionWarningBox = document.getElementById('vision-forgery-warning');
    if (visionWarningBox) visionWarningBox.style.display = 'none';
}

// ── 3. TRANSLATE (Split-Screen) ─────────────────────────────────────
let vendorMicActive = false;
let touristMicActive = false;

function toggleVendorMic() {
    const btn = document.querySelector('.mic-vendor');
    const waves = document.querySelector('.wave-vendor');
    vendorMicActive = !vendorMicActive;
    
    if (vendorMicActive) {
        if (navigator.vibrate) navigator.vibrate([30, 30, 30]);
        btn.classList.add('recording');
        waves.style.display = 'flex';
        // Reset tourist if active
        if(touristMicActive) toggleTouristMic();
    } else {
        if (navigator.vibrate) navigator.vibrate(50);
        btn.classList.remove('recording');
        waves.style.display = 'none';
        
        // Mock translate
        setTimeout(() => {
            document.getElementById('tourist-text').textContent = "Yes, that bowl is 120,000 VND.";
            if (navigator.vibrate) navigator.vibrate(30);
        }, 1000);
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
        // Reset vendor if active
        if(vendorMicActive) toggleVendorMic();
    } else {
        if (navigator.vibrate) navigator.vibrate(50);
        btn.classList.remove('recording');
        waves.style.display = 'none';
        
        // Mock translate
        setTimeout(() => {
            document.getElementById('vendor-text').textContent = "Vâng, bát đó giá 120.000 đồng.";
            if (navigator.vibrate) navigator.vibrate(30);
        }, 1000);
    }
}

// ── 4. GUARDIAN (Safety Listening) ──────────────────────────────────
let guardianListening = false;
let guardianRecognition = null;

if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    guardianRecognition = new SpeechRecognition();
    guardianRecognition.lang = 'vi-VN'; // Assuming Vietnamese for the demo
    guardianRecognition.continuous = true;
    guardianRecognition.interimResults = false;
    
    guardianRecognition.onresult = function(event) {
        const transcript = event.results[event.results.length - 1][0].transcript;
        const inputElement = document.getElementById('incident-input');
        if(inputElement) inputElement.value = transcript;
        
        // Auto stop and analyze when speech is detected
        if (guardianListening) {
            toggleGuardian(); // This will stop it and trigger analyzeScam()
        }
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
        
        if (guardianRecognition) {
            try { guardianRecognition.start(); } catch(e) {}
        } else {
            alert("Your browser does not support Speech Recognition. Please type manually.");
        }
    } else {
        if (navigator.vibrate) navigator.vibrate(50);
        btn.classList.remove('listening');
        status.textContent = "TAP TO LISTEN";
        status.style.color = "var(--neon-yellow)";
        
        if (guardianRecognition) {
            try { guardianRecognition.stop(); } catch(e) {}
        }
        analyzeScam();
    }
}

async function analyzeScam() {
    if (navigator.vibrate) navigator.vibrate([30, 30]);
    
    const inputElement = document.getElementById('incident-input');
    const userText = inputElement ? inputElement.value.trim() : "";
    
    // Default mock response
    let backendResponse = {
        tier: "EXTREME_OVERCHARGE",
        active_defense_script: "Tôi biết giá gốc của bánh rán chỉ khoảng 25,000 đồng. Yêu cầu 400,000 đồng là quá vô lý. Vui lòng nhận 25,000 đồng hoặc tôi sẽ gọi cảnh sát.",
        blackbox_triggered: true,
        nearest_authority: {
            name: "Công An Phường Hàng Bạc",
            distance_km: 0.3
        }
    };
    
    if (userText) {
        try {
            const btn = document.querySelector('.btn-secondary-giant');
            const originalBtnText = btn ? btn.innerHTML : "ANALYZE TEXT";
            if (btn) btn.innerHTML = "ANALYZING...";
            
            const res = await fetch('http://127.0.0.1:8000/api/v1/analyze-situation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    description: userText,
                    location: "Hoan Kiem Walking Street, Hanoi",
                    language: "vi",
                    lat: 21.0285,
                    lng: 105.8542
                })
            });
            const data = await res.json();
            
            if (btn) btn.innerHTML = originalBtnText;
            
            if (data && data.price_assessment) {
                backendResponse = {
                    tier: data.price_assessment.tier,
                    active_defense_script: data.active_defense_script || "Please negotiate carefully or refuse the service.",
                    blackbox_triggered: data.blackbox_triggered,
                    nearest_authority: data.nearest_authority || { name: "Công An Phường", distance_km: 0.5 }
                };
            }
        } catch (e) {
            console.error("Backend unreachable, falling back to mock.", e);
        }
    }

    // Show response
    setTimeout(() => {
        if (navigator.vibrate) navigator.vibrate([100, 50, 100]); // Danger pattern

        const alertTitle = document.getElementById('guardian-alert-title');
        const alertMsg = document.getElementById('guardian-alert-msg');
        const dispatchBox = document.getElementById('auto-dispatch-box');
        const authName = document.getElementById('dispatch-auth-name');
        
        if(alertTitle) alertTitle.innerText = backendResponse.tier.replace("_", " ");
        if(alertMsg) alertMsg.innerText = "Actionable Advice: " + backendResponse.active_defense_script;
        
        if (backendResponse.blackbox_triggered && dispatchBox) {
            activateBlackboxIndicator();
            dispatchBox.style.display = 'block';
            if(authName) authName.innerText = `Nearest Authority: ${backendResponse.nearest_authority.name} (${backendResponse.nearest_authority.distance_km}km)`;
        } else if (dispatchBox) {
            dispatchBox.style.display = 'none';
        }
        
        document.getElementById('scam-results-overlay').style.display = 'flex';
    }, 500);
}

// Auto Dispatch Action
window.dispatchReport = function() {
    if (navigator.vibrate) navigator.vibrate([100]);
    const btn = document.querySelector('.btn-secondary-giant');
    const statusMsg = document.getElementById('dispatch-status-msg');
    
    if(btn) {
        btn.innerHTML = "DISPATCHING...";
        btn.style.opacity = "0.7";
    }
    
    // Simulate API call to /api/v1/dispatch-report
    setTimeout(() => {
        if (navigator.vibrate) navigator.vibrate([50, 50, 50]);
        if(btn) {
            btn.innerHTML = "DISPATCHED ✓";
            btn.style.backgroundColor = "transparent";
            btn.style.color = "var(--neon-green)";
            btn.style.border = "2px solid var(--neon-green)";
            btn.disabled = true;
        }
        if(statusMsg) {
            statusMsg.innerText = "Official report securely sent to authorities.";
        }
    }, 2000);
};

function closeScamResults() {
    if (navigator.vibrate) navigator.vibrate(20);
    document.getElementById('scam-results-overlay').style.display = 'none';
}

// ── 5. SOS (Slide to SOS) ───────────────────────────────────────────
function initSlideToSOS() {
    const knob = document.getElementById('sos-knob');
    const track = document.querySelector('.slide-track');
    if (!knob || !track) return;

    let isDragging = false;
    let startX = 0;
    let currentX = 0;
    
    // The max distance the knob can travel
    const maxDragX = track.clientWidth - knob.clientWidth - 8; // 8px padding
    let triggered = false;

    function startDrag(e) {
        if(triggered) return;
        isDragging = true;
        startX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX;
        knob.style.transition = 'none'; // Disable transition while dragging
    }

    function doDrag(e) {
        if (!isDragging || triggered) return;
        
        const clientX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX;
        currentX = clientX - startX;
        
        // Clamp values
        if (currentX < 0) currentX = 0;
        if (currentX > maxDragX) currentX = maxDragX;
        
        knob.style.transform = `translateX(${currentX}px)`;

        // Trigger condition (e.g., dragged 95% of the way)
        if (currentX >= maxDragX * 0.95 && !triggered) {
            triggerSOS();
        }
    }

    function endDrag() {
        if (!isDragging) return;
        isDragging = false;
        
        if (!triggered) {
            // Snap back
            knob.style.transition = 'transform 0.3s var(--spring)';
            knob.style.transform = 'translateX(0)';
            currentX = 0;
        }
    }

    // Touch events
    knob.addEventListener('touchstart', startDrag, {passive: true});
    window.addEventListener('touchmove', doDrag, {passive: true});
    window.addEventListener('touchend', endDrag);

    // Mouse events (for desktop testing)
    knob.addEventListener('mousedown', startDrag);
    window.addEventListener('mousemove', doDrag);
    window.addEventListener('mouseup', endDrag);

    function triggerSOS() {
        triggered = true;
        knob.style.transform = `translateX(${maxDragX}px)`;
        knob.style.backgroundColor = '#00FF66'; // Turn green to confirm
        knob.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        
        // Heavy SOS Haptic Pattern
        if (navigator.vibrate) navigator.vibrate([100, 50, 100, 50, 300, 100, 300]);
        
        document.getElementById('sos-dispatch-status').innerHTML = "DISPATCHING SOS... LOCATION SHARED.";
        
        // Reset after 3 seconds
        setTimeout(() => {
            triggered = false;
            knob.style.transition = 'transform 0.5s ease';
            knob.style.transform = 'translateX(0)';
            knob.style.backgroundColor = 'var(--danger-red)';
            knob.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>`;
            document.getElementById('sos-dispatch-status').innerHTML = "";
            currentX = 0;
        }, 3000);
    }
}

// ==========================================
// 6. ULTIMATE UPGRADES LOGIC
// ==========================================

function activateBlackboxIndicator() {
    const indicator = document.getElementById('blackbox-indicator');
    if(indicator) {
        indicator.style.display = 'flex';
        // Hide after 10 seconds for demo
        setTimeout(() => {
            indicator.style.display = 'none';
        }, 10000);
    }
}

// Initialize Heatmap Data (Mocked for Demo)
async function initHeatmap() {
    const heatmapLayer = document.getElementById('heatmap-layer');
    if(heatmapLayer) {
        heatmapLayer.style.display = 'block';
        console.log("Heatmap data loaded and rendered.");
    }
}

// Call it when the SOS tab is shown
document.addEventListener('DOMContentLoaded', () => {
    const sosTabBtn = document.querySelector('[data-target="sos"]');
    if(sosTabBtn) {
        sosTabBtn.addEventListener('click', initHeatmap);
    }
});

// ==========================================
// 7. REAL-TIME CAMERA CAPTURE
// ==========================================

async function handlePricePhoto(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
    
    // Convert file to Base64
    const reader = new FileReader();
    reader.onload = async function(e) {
        const base64Image = e.target.result.split(',')[1]; // Remove data URL prefix
        
        // Show loading state
        const scanTitle = document.getElementById('scan-alert-title');
        const scanPrice = document.getElementById('scan-alert-price');
        const scanMsg = document.getElementById('scan-alert-msg');
        const overlay = document.getElementById('price-results-overlay');
        const visionWarningBox = document.getElementById('vision-forgery-warning');
        
        scanTitle.innerText = "ANALYZING IMAGE...";
        scanPrice.innerText = "...";
        scanMsg.innerText = "Please wait, AI is analyzing the layout...";
        if(visionWarningBox) visionWarningBox.style.display = 'none';
        
        scanTitle.parentElement.className = "results-card high-contrast tier-caution";
        overlay.style.display = 'flex';
        
        try {
            const response = await fetch('/api/v1/analyze-vision', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image_base64: base64Image,
                    language: currentLang
                })
            });
            const data = await response.json();
            
            if (data.status === 'success' && data.vision_assessment) {
                const assessment = data.vision_assessment;
                if (assessment.forgery_detected) {
                    scanTitle.innerText = "FORGERY DETECTED";
                    scanTitle.parentElement.className = "results-card high-contrast tier-danger";
                    scanMsg.innerText = assessment.analysis_reason;
                    
                    if (visionWarningBox) {
                        visionWarningBox.style.display = 'block';
                        document.getElementById('vision-reason').innerText = `Items detected: ${assessment.detected_items.join(", ")}`;
                    }
                    if (navigator.vibrate) navigator.vibrate([300, 200, 300]);
                } else {
                    scanTitle.innerText = "NO FORGERY";
                    scanTitle.parentElement.className = "results-card high-contrast tier-fair";
                    scanMsg.innerText = "The menu/receipt layout appears normal and safe.";
                }
            } else {
                scanTitle.innerText = "ANALYSIS FAILED";
                scanMsg.innerText = data.message || "Failed to contact Vision API.";
            }
        } catch (err) {
            console.error(err);
            scanTitle.innerText = "NETWORK ERROR";
            scanMsg.innerText = "Could not reach the server.";
        }
        
        // Reset input so the same file can be selected again
        event.target.value = '';
    };
    reader.readAsDataURL(file);
}

// End of app.js
