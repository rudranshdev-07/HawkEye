/**
 * HawkEye Advanced Frontend Application
 * 
 * Geospatial crime intelligence platform with interactive map analysis,
 * real-time risk assessment, forecasting, trends, and route analysis.
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

const CONFIG = {
    API_URL: "http://127.0.0.1:8000",
    API_TIMEOUT: 10000,
    TILE_ATTRIBUTION: "© HawkEye Intelligence | © OpenStreetMap contributors",
    DEFAULT_CENTER: [28.61, 77.20],
    DEFAULT_ZOOM: 10,
    DEBUG_MODE: true
};

// =============================================================================
// GLOBAL STATE
// =============================================================================

let map;
let marker;
let heatLayer;
let lastQuery = null;
let apiTimeout = null;
let heatmapVisible = false;
let routeMode = false;
let routePoints = [];
let drawnLayer;
let selectedCrimeTypes = [];
let trendsChart = null;

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener("DOMContentLoaded", function() {
    initializeMap();
    initializeControls();
    checkServerHealth();
    setupTabNavigation();
    logDebug("🚀 HawkEye frontend initialized with advanced features");
});

/**
 * Initialize Leaflet map with base layers and event handlers
 */
function initializeMap() {
    try {
        map = L.map('map').setView(CONFIG.DEFAULT_CENTER, CONFIG.DEFAULT_ZOOM);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: CONFIG.TILE_ATTRIBUTION,
            maxZoom: 18
        }).addTo(map);

        // Initialize Leaflet Draw
        drawnLayer = new L.FeatureGroup();
        map.addLayer(drawnLayer);

        const drawControl = new L.Control.Draw({
            draw: {
                polygon: false,
                polyline: true,
                rectangle: false,
                circle: false,
                marker: false
            },
            edit: {
                featureGroup: drawnLayer
            }
        });
        map.addControl(drawControl);

        map.on('draw:created', handleRouteDrawn);
        map.on('click', handleMapClick);

        logDebug(`✓ Map initialized at ${CONFIG.DEFAULT_CENTER}`);
    } catch (err) {
        showError(`Failed to initialize map: ${err.message}`);
        logDebug(`❌ Map init error: ${err}`);
    }
}

/**
 * Initialize UI controls and event listeners
 */
function initializeControls() {
    document.getElementById("toggleHeatmap").addEventListener("click", toggleHeatmap);
    document.getElementById("toggleRouteMode").addEventListener("click", toggleRouteMode);
    document.getElementById("clearFilters").addEventListener("click", clearCrimeFilters);

    // Crime filter checkboxes
    document.querySelectorAll(".crime-filter").forEach(checkbox => {
        checkbox.addEventListener("change", updateCrimeFilters);
    });
}

/**
 * Setup tab navigation
 */
function setupTabNavigation() {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            const tabName = this.getAttribute("data-tab");
            showTab(tabName);
        });
    });
}

// =============================================================================
// HEATMAP MANAGEMENT
// =============================================================================

async function toggleHeatmap() {
    try {
        const btn = document.getElementById("toggleHeatmap");
        
        if (heatmapVisible) {
            // Hide heatmap
            if (heatLayer) {
                map.removeLayer(heatLayer);
            }
            heatmapVisible = false;
            btn.textContent = "Heat Map OFF";
            btn.style.background = "rgba(56, 189, 248, 0.2)";
            logDebug("🔴 Heatmap disabled");
        } else {
            // Load and show heatmap
            showLoading();
            logDebug("📍 Loading heatmap data...");
            
            const response = await fetch(`${CONFIG.API_URL}/heatmap-data`);
            const data = await response.json();
            
            if (heatLayer) {
                map.removeLayer(heatLayer);
            }
            
            heatLayer = L.heatLayer(data.heatpoints, {
                radius: 25,
                blur: 15,
                maxZoom: 1,
                gradient: {0.2: '#0284c7', 0.4: '#06b6d4', 0.6: '#f59e0b', 0.8: '#ef4444', 1.0: '#7f1d1d'}
            }).addTo(map);
            
            heatmapVisible = true;
            btn.textContent = "Heat Map ON";
            btn.style.background = "rgba(236, 72, 153, 0.3)";
            hideLoading();
            logDebug("✅ Heatmap enabled");
        }
    } catch (err) {
        showError(`Failed to load heatmap: ${err.message}`);
        logDebug(`❌ Heatmap error: ${err}`);
    }
}

// =============================================================================
// ROUTE MODE
// =============================================================================

function toggleRouteMode() {
    const btn = document.getElementById("toggleRouteMode");
    
    if (routeMode) {
        routeMode = false;
        routePoints = [];
        drawnLayer.clearLayers();
        btn.textContent = "Draw Route";
        btn.style.background = "rgba(56, 189, 248, 0.2)";
        logDebug("🛣️ Route drawing disabled");
    } else {
        routeMode = true;
        btn.textContent = "Route Mode ON (Click to add points)";
        btn.style.background = "rgba(236, 72, 153, 0.3)";
        logDebug("🛣️ Route mode enabled");
    }
}

function handleRouteDrawn(e) {
    const layer = e.layer;
    drawnLayer.addLayer(layer);
    analyzeRoute(layer);
}

async function analyzeRoute(layer) {
    try {
        const latlngs = layer.getLatLngs();
        if (latlngs.length < 2) return;

        showLoading();
        logDebug(`🛣️ Analyzing route with ${latlngs.length} waypoints...`);

        const waypoints = latlngs.map(ll => [ll.lat, ll.lng]);

        const response = await fetch(`${CONFIG.API_URL}/route-safety`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ waypoints })
        });

        const data = await response.json();
        displayRouteAnalysis(data);
        
        document.getElementById("advancedTabs").style.display = "block";
        showTab("routes");
        hideLoading();
    } catch (err) {
        showError(`Failed to analyze route: ${err.message}`);
        logDebug(`❌ Route analysis error: ${err}`);
    }
}

function displayRouteAnalysis(data) {
    const container = document.getElementById("routeAnalysis");
    
    let html = `
        <div style="margin-bottom: 12px;">
            <strong>Overall Route Risk: ${data.overall_route_risk}</strong> (${data.overall_risk_level})
        </div>
        <div class="route-recommendations">
            <ul>
                ${data.recommendations.map(r => `<li>${r}</li>`).join('')}
            </ul>
        </div>
        <div style="margin-top: 12px;">
            <strong>Segments:</strong>
            ${data.segments.map(s => `
                <div class="route-segment">
                    Segment ${s.segment_index}: Risk ${s.segment_risk_score} (${s.segment_risk_level})
                </div>
            `).join('')}
        </div>
    `;
    
    container.innerHTML = html;
}

// =============================================================================
// CRIME TYPE FILTERING
// =============================================================================

function updateCrimeFilters() {
    selectedCrimeTypes = Array.from(document.querySelectorAll(".crime-filter:checked"))
        .map(cb => cb.value);
    
    logDebug(`🔍 Filters updated: ${selectedCrimeTypes.length > 0 ? selectedCrimeTypes.join(", ") : "None"}`);
    
    if (lastQuery) {
        queryLocationIntelligence(lastQuery.lat, lastQuery.lon);
    }
}

function clearCrimeFilters() {
    document.querySelectorAll(".crime-filter").forEach(cb => cb.checked = false);
    selectedCrimeTypes = [];
    logDebug("🔍 All filters cleared");
}

// =============================================================================
// MAP INTERACTION
// =============================================================================

async function handleMapClick(e) {
    if (routeMode) return;

    const lat = e.latlng.lat;
    const lon = e.latlng.lng;

    logDebug(`📍 Map clicked: (${lat.toFixed(4)}, ${lon.toFixed(4)})`);

    if (marker) {
        map.removeLayer(marker);
    }
    marker = L.marker([lat, lon]).addTo(map);

    await queryLocationIntelligence(lat, lon);
}

/**
 * Query the risk intelligence API for a location
 */
async function queryLocationIntelligence(lat, lon) {
    try {
        lastQuery = { lat, lon };

        showLoading();
        logDebug(`🔄 Querying intelligence API...`);

        const controller = new AbortController();
        apiTimeout = setTimeout(() => controller.abort(), CONFIG.API_TIMEOUT);

        const response = await fetch(`${CONFIG.API_URL}/risk`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                features: { latitude: lat, longitude: lon },
                crime_types: selectedCrimeTypes,
                include_forecast: true,
                include_trends: true
            }),
            signal: controller.signal
        });

        clearTimeout(apiTimeout);

        if (!response.ok) {
            throw new Error(`Server error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        displayIntelligence(data);

        // Load forecast
        loadForecast(lat, lon);
        
        // Load trends
        loadTrends(lat, lon);

        logDebug(`✓ Intelligence received: risk=${data.risk_score}, level=${data.risk_level}`);

        document.getElementById("advancedTabs").style.display = "block";

    } catch (err) {
        clearTimeout(apiTimeout);

        if (err.name === "AbortError") {
            showError(`Request timeout (${CONFIG.API_TIMEOUT}ms). Server may be slow.`);
            logDebug(`❌ API timeout`);
        } else {
            showError(`Failed to analyze location: ${err.message}`);
            logDebug(`❌ API error: ${err.message}`);
        }

        hideLoading();
    }
}

// =============================================================================
// FORECAST
// =============================================================================

async function loadForecast(lat, lon) {
    try {
        const response = await fetch(`${CONFIG.API_URL}/forecast?latitude=${lat}&longitude=${lon}`);
        const data = await response.json();
        displayForecast(data);
    } catch (err) {
        logDebug(`⚠️ Forecast load failed: ${err.message}`);
    }
}

function displayForecast(data) {
    const container = document.getElementById("forecastContainer");
    
    let html = `<div class="forecast-grid">`;
    
    data.forecasts.forEach(f => {
        const riskColor = getRiskColor(f.predicted_risk_score);
        html += `
            <div class="forecast-hour" style="border-left: 3px solid ${riskColor}">
                <div class="forecast-hour-time">${f.hour}:00</div>
                <div class="forecast-hour-risk">${f.predicted_risk_score}</div>
                <div style="font-size: 10px; color: #94a3b8;">${f.confidence * 100}%</div>
            </div>
        `;
    });
    
    html += `</div>`;
    
    if (data.safest_hours.length > 0) {
        html += `<p><strong>Safest Hours:</strong> ${data.safest_hours.join(", ")}</p>`;
    }
    if (data.dangerous_hours.length > 0) {
        html += `<p><strong>Dangerous Hours:</strong> ${data.dangerous_hours.join(", ")}</p>`;
    }
    
    container.innerHTML = html;
}

// =============================================================================
// TRENDS
// =============================================================================

async function loadTrends(lat, lon) {
    try {
        const response = await fetch(`${CONFIG.API_URL}/trends?latitude=${lat}&longitude=${lon}`);
        const data = await response.json();
        displayTrends(data);
    } catch (err) {
        logDebug(`⚠️ Trends load failed: ${err.message}`);
    }
}

function displayTrends(data) {
    const ctx = document.getElementById("trendsChart").getContext("2d");
    
    const labels = data.trends.map(t => t.period);
    const counts = data.trends.map(t => t.crime_count);
    
    if (trendsChart) {
        trendsChart.destroy();
    }
    
    trendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Crime Count',
                data: counts,
                borderColor: '#38bdf8',
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                tension: 0.4,
                fill: true,
                borderWidth: 2,
                pointBackgroundColor: '#38bdf8',
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#e2e8f0' }
                }
            },
            scales: {
                y: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: '#1e293b' }
                },
                x: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: '#1e293b' }
                }
            }
        }
    });
}

// =============================================================================
// UI UPDATES
// =============================================================================

/**
 * Display comprehensive intelligence report
 */
function displayIntelligence(data) {
    hideLoading();

    const riskEmoji = getRiskEmoji(data.risk_score);
    const riskColor = getRiskColor(data.risk_score);

    const topCrimesHTML = Object.entries(data.top_crimes)
        .map(([crime, count]) => `<li>${crime}: ${count}</li>`)
        .join('');

    let safetyTipsHTML = '';
    if (data.safety_tips && data.safety_tips.length > 0) {
        safetyTipsHTML = `
            <div class="section safety-tips">
                <h4>🛡️ Safety Tips</h4>
                ${data.safety_tips.map(tip => `
                    <div class="safety-tip ${tip.priority}">
                        ${tip.tip}
                    </div>
                `).join('')}
            </div>
        `;
    }

    const resultHTML = `
        <div class="intelligence-report">
            <div class="score-card">
                <div class="score-badge" style="background: ${riskColor}">
                    ${data.risk_score.toFixed(1)}
                </div>
                <div class="score-details">
                    <h3>${riskEmoji} ${data.risk_level}</h3>
                    <p>Risk Assessment</p>
                </div>
            </div>

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

            <div class="section">
                <h4>🚨 Crime Profile</h4>
                <p><strong>Dominant Crime:</strong> ${data.dominant_crime}</p>
                <p><strong>Top Crimes:</strong></p>
                <ul>${topCrimesHTML || '<li>No data</li>'}</ul>
            </div>

            <div class="section">
                <h4>⚠️ Risk Factors</h4>
                <ul>
                    ${data.reasons.map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>

            ${safetyTipsHTML}

            <div class="section">
                <p><strong>Population Density:</strong> ${data.population_density} people/km²</p>
                <p><strong>Query:</strong> (${data.latitude?.toFixed(4) || 'N/A'}, ${data.longitude?.toFixed(4) || 'N/A'})</p>
            </div>
        </div>
    `;

    document.getElementById("resultBox").innerHTML = resultHTML;
}

/**
 * Tab navigation
 */
function showTab(tabName) {
    document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    
    document.getElementById(`${tabName}-tab`).classList.add("active");
    document.querySelector(`[data-tab="${tabName}"]`).classList.add("active");
}

// =============================================================================
// SERVER HEALTH
// =============================================================================

async function checkServerHealth() {
    try {
        const response = await fetch(`${CONFIG.API_URL}/health`, { timeout: 5000 });

        if (response.ok) {
            const data = await response.json();
            updateServerStatus(true, `Dataset ready (${data.dataset_size} records)`);
            logDebug(`✓ Server healthy`);
        } else {
            updateServerStatus(false, "Server error");
        }
    } catch (err) {
        updateServerStatus(false, "Server unavailable");
    }
}

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
// UI UTILITIES
// =============================================================================

function showLoading() {
    document.getElementById("resultCard").style.display = "none";
    document.getElementById("loadingCard").style.display = "block";
    document.getElementById("errorCard").style.display = "none";
}

function hideLoading() {
    document.getElementById("loadingCard").style.display = "none";
    document.getElementById("resultCard").style.display = "block";
}

function showError(message) {
    document.getElementById("loadingCard").style.display = "none";
    document.getElementById("resultCard").style.display = "none";
    document.getElementById("errorCard").style.display = "block";
    document.getElementById("errorText").textContent = message;
}

function hideError() {
    document.getElementById("errorCard").style.display = "none";
    document.getElementById("resultCard").style.display = "block";
}

function getRiskColor(score) {
    if (score >= 80) return "#7f1d1d";
    if (score >= 60) return "#b91c1c";
    if (score >= 40) return "#f59e0b";
    if (score >= 20) return "#6366f1";
    return "#22c55e";
}

function getRiskEmoji(score) {
    if (score >= 80) return "🚨";
    if (score >= 60) return "⚠️";
    if (score >= 40) return "🟡";
    if (score >= 20) return "🟢";
    return "✅";
}

function logDebug(msg) {
    if (!CONFIG.DEBUG_MODE) return;
    
    const timestamp = new Date().toLocaleTimeString();
    const debugPanel = document.getElementById("debugPanel");
    const entry = `<div>[${timestamp}] ${msg}</div>`;
    
    debugPanel.innerHTML += entry;
    debugPanel.parentElement.scrollTop = debugPanel.parentElement.scrollHeight;
}
