/**
 * HawkEye Frontend Application
 * 
 * Geospatial crime intelligence platform with interactive map analysis,
 * real-time risk assessment, and explainable AI insights.
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

const CONFIG = {
    API_URL: "http://127.0.0.1:8000",
    API_TIMEOUT: 10000,           // 10 second timeout
    TILE_ATTRIBUTION: "© HawkEye Intelligence | © OpenStreetMap contributors",
    DEFAULT_CENTER: [28.61, 77.20], // India center
    DEFAULT_ZOOM: 10,
    DEBUG_MODE: true              // Set to false to hide debug info
};

// =============================================================================
// GLOBAL STATE
// =============================================================================

let map;
let marker;
let heatLayer;
let lastQuery = null;
let apiTimeout = null;

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener("DOMContentLoaded", function() {
    initializeMap();
    checkServerHealth();
    logDebug("🚀 HawkEye frontend initialized");
});

/**
 * Initialize Leaflet map with base layers and event handlers
 */
function initializeMap() {
    try {
        // Create map centered on India
        map = L.map('map').setView(CONFIG.DEFAULT_CENTER, CONFIG.DEFAULT_ZOOM);

        // Add OSM base layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: CONFIG.TILE_ATTRIBUTION,
            maxZoom: 18
        }).addTo(map);

        // Add click handler for location analysis
        map.on('click', handleMapClick);

        logDebug(`✓ Map initialized at ${CONFIG.DEFAULT_CENTER}`);
    } catch (err) {
        showError(`Failed to initialize map: ${err.message}`);
        logDebug(`❌ Map initialization error: ${err}`);
    }
}

/**
 * Check if backend API is healthy
 */
async function checkServerHealth() {
    try {
        const response = await fetch(`${CONFIG.API_URL}/health`, {
            timeout: 5000
        });

        if (response.ok) {
            const data = await response.json();
            updateServerStatus(true, `Dataset ready (${data.dataset_size} records)`);
            logDebug(`✓ Server healthy: ${data.dataset_size} records loaded`);
        } else {
            updateServerStatus(false, "Server error");
            logDebug(`❌ Server health check failed: ${response.status}`);
        }
    } catch (err) {
        updateServerStatus(false, "Server unavailable");
        logDebug(`❌ Cannot connect to server: ${err.message}`);
    }
}

/**
 * Update server status indicator in UI
 */
function updateServerStatus(healthy, message) {
    const statusEl = document.getElementById("serverStatus");
    const statusIndicator = statusEl.querySelector(".status-indicator");
    const statusText = document.getElementById("statusText");

    if (healthy) {
        statusIndicator.classList.remove("checking", "error");
        statusIndicator.classList.add("healthy");
    } else {
        statusIndicator.classList.remove("checking");
        statusIndicator.classList.add("error");
    }

    statusText.textContent = message;
}

// =============================================================================
// MAP INTERACTION
// =============================================================================

/**
 * Handle map click to query location intelligence
 */
async function handleMapClick(e) {
    const lat = e.latlng.lat;
    const lon = e.latlng.lng;

    logDebug(`📍 Map clicked: (${lat.toFixed(4)}, ${lon.toFixed(4)})`);

    // Update marker
    if (marker) {
        map.removeLayer(marker);
    }
    marker = L.marker([lat, lon]).addTo(map);

    // Query intelligence
    await queryLocationIntelligence(lat, lon);
}

/**
 * Query the risk intelligence API for a location
 */
async function queryLocationIntelligence(lat, lon) {
    try {
        lastQuery = { lat, lon };

        // Show loading state
        showLoading();
        logDebug(`🔄 Querying intelligence API...`);

        // Set timeout for API call
        const controller = new AbortController();
        apiTimeout = setTimeout(() => controller.abort(), CONFIG.API_TIMEOUT);

        const response = await fetch(`${CONFIG.API_URL}/risk`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                features: {
                    latitude: lat,
                    longitude: lon
                }
            }),
            signal: controller.signal
        });

        clearTimeout(apiTimeout);

        // Handle response
        if (!response.ok) {
            throw new Error(`Server error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        displayIntelligence(data);

        logDebug(`✓ Intelligence received: risk=${data.risk_score}, level=${data.risk_level}`);

    } catch (err) {
        clearTimeout(apiTimeout);

        if (err.name === "AbortError") {
            showError(`Request timeout (${CONFIG.API_TIMEOUT}ms). Server may be slow or unreachable.`);
            logDebug(`❌ API timeout after ${CONFIG.API_TIMEOUT}ms`);
        } else {
            showError(`Failed to analyze location: ${err.message}`);
            logDebug(`❌ API error: ${err.message}`);
        }

        hideLoading();
    }
}

// =============================================================================
// UI UPDATES
// =============================================================================

/**
 * Display comprehensive intelligence report
 */
function displayIntelligence(data) {
    hideLoading();

    // Build risk color and emoji
    const riskEmoji = getRiskEmoji(data.risk_score);
    const riskColor = getRiskColor(data.risk_score);

    // Format top crimes
    const topCrimesHTML = Object.entries(data.top_crimes)
        .map(([crime, count]) => `<li>${crime}: ${count}</li>`)
        .join("") || "<li>No data</li>";

    // Build reasons list
    const reasonsHTML = data.reasons
        .map(reason => `<li>${reason}</li>`)
        .join("");

    // Main result HTML
    const html = `
        <div class="intelligence-report" style="border-left: 4px solid ${riskColor};">
            
            <!-- Risk Score Card -->
            <div class="score-card">
                <div class="score-badge" style="background: ${riskColor};">
                    <span class="score-number">${data.risk_score}</span>
                </div>
                <div class="score-details">
                    <h3 style="color: ${riskColor}; margin: 0;">${riskEmoji} ${data.risk_level}</h3>
                    <p style="margin: 0; font-size: 0.9em; color: #aaa;">Risk Assessment</p>
                </div>
            </div>

            <!-- Crime Stats Grid -->
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-label">Total Crimes (5km)</div>
                    <div class="stat-value">${data.crime_count}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Within 1km</div>
                    <div class="stat-value">${data.crimes_1km}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Within 3km</div>
                    <div class="stat-value">${data.crimes_3km}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Within 5km</div>
                    <div class="stat-value">${data.crimes_5km}</div>
                </div>
            </div>

            <!-- Crime Profile -->
            <div class="section">
                <h4>🚨 Crime Profile</h4>
                <p><strong>Dominant Crime:</strong> ${data.dominant_crime}</p>
                <p><strong>Top Crimes:</strong></p>
                <ul style="margin: 5px 0; padding-left: 20px;">
                    ${topCrimesHTML}
                </ul>
            </div>

            <!-- Hotspot Information -->
            ${data.nearest_hotspot_distance_km !== null ? `
            <div class="section">
                <h4>🔴 Hotspot Proximity</h4>
                <p><strong>Distance:</strong> ${data.nearest_hotspot_distance_km.toFixed(2)} km</p>
                <p><strong>Hotspot Rank:</strong> #${data.nearest_hotspot_rank}</p>
                <p><strong>Incidents in Hotspot:</strong> ${data.hotspot_incidents}</p>
            </div>
            ` : ""}

            <!-- Risk Factors -->
            <div class="section">
                <h4>⚠️ Risk Factors</h4>
                <ul style="padding-left: 20px; margin: 5px 0;">
                    ${reasonsHTML}
                </ul>
            </div>

            <!-- Location Details -->
            <div class="section" style="background: #0f172a; padding: 8px; border-radius: 6px; font-size: 0.9em;">
                <p><strong>Population Density:</strong> ${data.population_density} people/km²</p>
                <p><strong>Severity Level:</strong> ${(data.severity || 0).toFixed(1)}/10</p>
                <p style="margin-top: 5px; color: #888; font-size: 0.85em;">Query: (${lastQuery.lat.toFixed(4)}, ${lastQuery.lon.toFixed(4)})</p>
            </div>
        </div>
    `;

    const resultBox = document.getElementById("resultBox");
    resultBox.innerHTML = html;

    logDebug(`✓ Intelligence displayed: score=${data.risk_score}`);
}

/**
 * Show loading spinner
 */
function showLoading() {
    document.getElementById("resultCard").style.display = "none";
    document.getElementById("loadingCard").style.display = "block";
    document.getElementById("errorCard").style.display = "none";
}

/**
 * Hide loading spinner
 */
function hideLoading() {
    document.getElementById("loadingCard").style.display = "none";
    document.getElementById("resultCard").style.display = "block";
}

/**
 * Show error message
 */
function showError(message) {
    document.getElementById("resultCard").style.display = "none";
    document.getElementById("errorCard").style.display = "block";
    document.getElementById("errorText").textContent = message;
    logDebug(`❌ Error shown: ${message}`);
}

/**
 * Hide error message
 */
function hideError() {
    document.getElementById("errorCard").style.display = "none";
    document.getElementById("resultCard").style.display = "block";
}

/**
 * Get risk color based on score
 */
function getRiskColor(score) {
    if (score >= 80) return "#ff0000";      // Red
    if (score >= 60) return "#ff8c00";      // Orange
    if (score >= 40) return "#ffff00";      // Yellow
    if (score >= 20) return "#90ee90";      // Light Green
    return "#00cc00";                       // Green
}

/**
 * Get risk emoji based on score
 */
function getRiskEmoji(score) {
    if (score >= 80) return "🚨";
    if (score >= 60) return "⚠️";
    if (score >= 40) return "⚡";
    if (score >= 20) return "✅";
    return "🟢";
}

// =============================================================================
// DEBUG LOGGING
// =============================================================================

/**
 * Log debug message to console and UI
 */
function logDebug(message) {
    if (CONFIG.DEBUG_MODE) {
        console.log(`[HawkEye] ${message}`);

        // Update debug panel
        const timestamp = new Date().toLocaleTimeString();
        const debugPanel = document.getElementById("debugPanel");
        const entry = document.createElement("div");
        entry.style.cssText = "padding: 3px 0; border-bottom: 1px solid #333; font-size: 0.85em; font-family: monospace;";
        entry.innerHTML = `<span style="color: #888;">[${timestamp}]</span> ${message}`;
        debugPanel.appendChild(entry);

        // Keep only last 20 entries
        const entries = debugPanel.querySelectorAll("div");
        if (entries.length > 20) {
            entries[0].remove();
        }
    }
}