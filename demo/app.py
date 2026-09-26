import asyncio
import http.server
import json
import mimetypes
import os
from pathlib import Path
import socketserver
import threading
import urllib.parse

PORT = 8000

# Global state for background agent runs
AGENT_STATE = {
    "status": "idle",
    "action": "none",
    "message": "Agent ready",
    "last_result": None,
    "started_at": 0,
}

FLOATING_BAR_HTML = """
<!-- Tireless Hand Floating Horizontal Agent Bar -->
<div id="tireless-floating-bar-container">
    <div id="tireless-floating-bar">
        <div class="tfb-brand">
            <span class="tfb-logo">🦾</span>
            <span class="tfb-title">Tireless Hand</span>
        </div>
        
        <div class="tfb-input-group">
            <input type="text" id="tfb-url-input" placeholder="http://localhost:8000/dashboard" value="http://localhost:8000/dashboard" />
        </div>

        <div class="tfb-options">
            <label class="tfb-checkbox-label">
                <input type="checkbox" id="tfb-headed-check">
                <span>👁️ Watch Live</span>
            </label>
        </div>

        <div class="tfb-actions">
            <button class="tfb-btn tfb-btn-primary" onclick="tfbRunAction('audit')">⚡ Audit</button>
            <button class="tfb-btn tfb-btn-secondary" onclick="tfbRunAction('explore')">🔍 Explore</button>
            <button class="tfb-btn tfb-btn-accent" onclick="tfbRunAction('benchmark')">📊 Benchmark</button>
            <a href="/reports/submission.html" target="_blank" class="tfb-btn tfb-btn-link">📄 Reports</a>
        </div>

        <div id="tfb-status-badge" class="tfb-badge tfb-badge-idle">
            <span class="tfb-dot"></span>
            <span id="tfb-status-text">Ready</span>
        </div>
    </div>

    <!-- Collapsible Output Drawer -->
    <div id="tfb-drawer">
        <div class="tfb-drawer-header">
            <strong id="tfb-drawer-title">Agent Execution Log</strong>
            <button class="tfb-drawer-close" onclick="tfbToggleDrawer(false)">✕</button>
        </div>
        <div id="tfb-drawer-content">
            <div style="color: #94a3b8; font-size: 13px;">No active runs. Choose an action above to test any web page autonomously.</div>
        </div>
    </div>
</div>

<style>
#tireless-floating-bar-container {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 999999;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    width: 92%;
    max-width: 960px;
}

#tireless-floating-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(15, 23, 42, 0.88);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    padding: 10px 18px;
    border-radius: 9999px;
    border: 1px solid rgba(56, 189, 248, 0.35);
    box-shadow: 0 20px 35px -5px rgba(0, 0, 0, 0.6), 0 0 20px rgba(56, 189, 248, 0.15);
    color: #f8fafc;
}

.tfb-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 700;
    font-size: 14px;
    color: #38bdf8;
    white-space: nowrap;
}
.tfb-logo { font-size: 18px; }

.tfb-input-group { flex: 1; min-width: 220px; }
#tfb-url-input {
    width: 100%;
    background: rgba(30, 41, 59, 0.85);
    border: 1px solid #334155;
    padding: 8px 14px;
    border-radius: 9999px;
    color: #f8fafc;
    font-size: 13px;
    outline: none;
    box-sizing: border-box;
    transition: all 0.2s ease;
}
#tfb-url-input:focus {
    border-color: #38bdf8;
    background: #0f172a;
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
}

.tfb-options { display: flex; align-items: center; font-size: 12px; color: #94a3b8; white-space: nowrap; }
.tfb-checkbox-label { display: flex; align-items: center; gap: 6px; cursor: pointer; user-select: none; }
.tfb-checkbox-label input { cursor: pointer; }

.tfb-actions { display: flex; align-items: center; gap: 8px; }
.tfb-btn {
    padding: 7px 14px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 600;
    border: none;
    cursor: pointer;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    text-decoration: none;
    white-space: nowrap;
}
.tfb-btn-primary { background: #0284c7; color: white; }
.tfb-btn-primary:hover { background: #0369a1; transform: translateY(-1px); }
.tfb-btn-secondary { background: #334155; color: #f8fafc; }
.tfb-btn-secondary:hover { background: #475569; transform: translateY(-1px); }
.tfb-btn-accent { background: #8b5cf6; color: white; }
.tfb-btn-accent:hover { background: #7c3aed; transform: translateY(-1px); }
.tfb-btn-link { background: #1e293b; color: #38bdf8; border: 1px solid rgba(56,189,248,0.3); }
.tfb-btn-link:hover { background: #334155; }

.tfb-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.tfb-badge-idle { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }
.tfb-badge-idle .tfb-dot { width: 7px; height: 7px; border-radius: 50%; background: #94a3b8; }

.tfb-badge-running { background: rgba(56, 189, 248, 0.2); color: #38bdf8; }
.tfb-badge-running .tfb-dot {
    width: 7px; height: 7px; border-radius: 50%; background: #38bdf8;
    box-shadow: 0 0 8px #38bdf8;
    animation: tfb-pulse 1.2s infinite;
}

.tfb-badge-success { background: rgba(16, 185, 129, 0.2); color: #10b981; }
.tfb-badge-success .tfb-dot { width: 7px; height: 7px; border-radius: 50%; background: #10b981; }

@keyframes tfb-pulse {
    0% { transform: scale(0.9); opacity: 0.7; }
    50% { transform: scale(1.3); opacity: 1; }
    100% { transform: scale(0.9); opacity: 0.7; }
}

#tfb-drawer {
    display: none;
    margin-bottom: 12px;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    max-height: 280px;
    overflow-y: auto;
}
.tfb-drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 8px;
    margin-bottom: 12px;
    color: #38bdf8;
    font-size: 13px;
}
.tfb-drawer-close {
    background: transparent;
    border: none;
    color: #64748b;
    font-size: 14px;
    cursor: pointer;
}
.tfb-drawer-close:hover { color: #f8fafc; }
</style>

<script>
let tfbPollInterval = null;

function tfbToggleDrawer(show) {
    const drawer = document.getElementById("tfb-drawer");
    if (drawer) {
        drawer.style.display = show ? "block" : "none";
    }
}

async function tfbRunAction(action) {
    const url = document.getElementById("tfb-url-input").value || window.location.href;
    const isHeaded = document.getElementById("tfb-headed-check").checked;

    const statusBadge = document.getElementById("tfb-status-badge");
    const statusText = document.getElementById("tfb-status-text");
    const drawerContent = document.getElementById("tfb-drawer-content");
    const drawerTitle = document.getElementById("tfb-drawer-title");

    statusBadge.className = "tfb-badge tfb-badge-running";
    statusText.innerText = "Running " + action.toUpperCase() + "...";
    drawerTitle.innerText = "Executing " + action.toUpperCase() + " on " + url;
    drawerContent.innerHTML = `<div style="color: #38bdf8;">[*] Starting autonomous agent (${action})... Please wait.</div>`;
    tfbToggleDrawer(true);

    try {
        const resp = await fetch("/api/run_" + action, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: url, headless: !isHeaded })
        });
        const data = await resp.json();
        
        // Start polling for results
        if (tfbPollInterval) clearInterval(tfbPollInterval);
        tfbPollInterval = setInterval(tfbCheckStatus, 1500);
    } catch (e) {
        statusBadge.className = "tfb-badge tfb-badge-idle";
        statusText.innerText = "Error";
        drawerContent.innerHTML = `<div style="color: #ef4444;">[X] Failed to launch agent: ` + e + `</div>`;
    }
}

async function tfbCheckStatus() {
    try {
        const resp = await fetch("/api/agent_status");
        const state = await resp.json();

        const statusBadge = document.getElementById("tfb-status-badge");
        const statusText = document.getElementById("tfb-status-text");
        const drawerContent = document.getElementById("tfb-drawer-content");

        if (state.status === "running") {
            statusBadge.className = "tfb-badge tfb-badge-running";
            statusText.innerText = state.action.toUpperCase() + " RUNNING...";
            drawerContent.innerHTML = `<div style="color: #38bdf8;">[*] ` + state.message + `</div>`;
        } else if (state.status === "done") {
            clearInterval(tfbPollInterval);
            tfbPollInterval = null;
            statusBadge.className = "tfb-badge tfb-badge-success";
            statusText.innerText = "DONE (100%)";

            let detailsHtml = `<div style="color: #10b981; font-weight: bold; margin-bottom: 8px;">[+] ` + state.message + `</div>`;
            if (state.last_result) {
                detailsHtml += `<div style="background: #1e293b; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 12px; color: #cbd5e1;">` + 
                    JSON.stringify(state.last_result, null, 2)
                        .replace(/\\n/g, '<br>')
                        .replace(/\\s/g, '&nbsp;') + 
                `</div>`;
            }
            detailsHtml += `<div style="margin-top: 10px; display: flex; gap: 10px;">
                <a href="/reports/submission.html" target="_blank" style="padding: 6px 12px; background: #0284c7; color: white; border-radius: 4px; text-decoration: none; font-size: 12px; font-weight: bold;">View Interactive HTML Report & Videos →</a>
                <a href="/reports/benchmark_results.json" target="_blank" style="padding: 6px 12px; background: #334155; color: white; border-radius: 4px; text-decoration: none; font-size: 12px;">Benchmark JSON Data</a>
            </div>`;

            drawerContent.innerHTML = detailsHtml;
        }
    } catch (e) {
        console.error("Status poll error:", e);
    }
}

// Auto-fill input with current URL on load
document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("tfb-url-input");
    if (input && window.location.pathname !== "/ui") {
        input.value = window.location.href;
    }
});
</script>
"""

HTML_HEADER = """
<header style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; border-bottom: 1px solid #334155; padding-bottom: 12px; margin-bottom: 20px;">
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 24px;">🚁</span>
        <h2 style="margin: 0; color: #38bdf8; font-size: 18px;">FlytBase Mission Control</h2>
    </div>
    <nav style="display: flex; gap: 12px; flex-wrap: wrap;">
        <a href="/dashboard?auth=1" style="color: #94a3b8; text-decoration: none; font-size: 13px;">Cockpit</a>
        <a href="/missions?auth=1" style="color: #94a3b8; text-decoration: none; font-size: 13px;">Missions</a>
        <a href="/fleet?auth=1" style="color: #94a3b8; text-decoration: none; font-size: 13px;">Fleet</a>
        <a href="/diagnostics?auth=1" style="color: #94a3b8; text-decoration: none; font-size: 13px;">Diagnostics</a>
        <a href="/settings?auth=1" style="color: #94a3b8; text-decoration: none; font-size: 13px;">Settings</a>
        <a href="/ui" style="color: #38bdf8; text-decoration: none; font-size: 13px; font-weight: bold; background: rgba(56,189,248,0.1); padding: 2px 8px; border-radius: 4px;">🦾 Agent HUD</a>
    </nav>
    <div style="font-size: 12px; color: #64748b;">Pilot: <strong style="color: #f8fafc;">Capt. Miller</strong></div>
</header>
"""

HTML_LOGIN = """<!DOCTYPE html>
<html>
<head>
    <title>FlytBase Mission Control - Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b1120; color: #f8fafc; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 32px; border-radius: 8px; width: 340px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h2 { margin-top: 0; color: #38bdf8; }
        label { font-size: 13px; color: #94a3b8; display: block; margin-top: 10px; }
        input { width: 100%; padding: 10px; margin: 6px 0 14px; border-radius: 4px; border: 1px solid #475569; background: #0f172a; color: white; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #0284c7; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🚁 Mission Control</h2>
        <form action="/login_submit" method="POST">
            <label>Operator Email</label>
            <input type="email" name="email" placeholder="pilot@flytbase.com" value="operator@flytbase.com" required>
            
            <label>Access Code / OTP</label>
            <input type="text" name="otp" placeholder="6-digit OTP" value="849201" required>

            __SUBMIT_BUTTON__
        </form>
    </div>
    __FLOATING_BAR__
</body>
</html>
"""

HTML_DASHBOARD = """<!DOCTYPE html>
<html>
<head>
    <title>FlytBase Mission Control - Fleet Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b1120; color: #f8fafc; margin: 0; padding: 20px 20px 100px; }
        .badge { padding: 4px 10px; border-radius: 4px; font-size: 13px; font-weight: bold; }
        .badge-offline { background: #ef4444; color: white; }
        .badge-online { background: #10b981; color: white; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
        .drone-card { background: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #334155; }
        .telemetry-row { display: flex; justify-content: space-between; margin: 8px 0; border-bottom: 1px solid #283548; padding-bottom: 4px; }
        .action-bar { margin-top: 16px; display: flex; gap: 10px; __ACTION_BAR_STYLE__ }
        .btn { padding: 10px 16px; border-radius: 4px; font-weight: bold; border: none; cursor: pointer; text-decoration: none; font-size: 13px; }
        .btn-rth { background: #e11d48; color: white; __RTH_BUTTON_STYLE__ }
        .btn-land { background: #d97706; color: white; }
    </style>
</head>
<body>
    __HEADER__
    <div class="grid">
        <div class="drone-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3>Drone Raven-X1</h3>
                <span class="badge __STATUS_BADGE_CLASS__">__STATUS_TEXT__</span>
            </div>
            
            <div class="telemetry-row"><span>Altitude</span><strong>124.5 m</strong></div>
            <div class="telemetry-row"><span>Ground Speed</span><strong>14.2 m/s</strong></div>
            <div class="telemetry-row"><span>Battery (LiPo)</span><strong>88% (24.2V)</strong></div>
            <div class="telemetry-row"><span>Video Stream</span><strong style="color: #38bdf8;">LIVE (1080p60)</strong></div>
            
            <div class="action-bar">
                <button class="btn btn-rth" id="btn-rth">Return To Home (RTH)</button>
                <button class="btn btn-land" id="btn-land">Auto Land</button>
            </div>
        </div>
    </div>
    __FLOATING_BAR__
</body>
</html>
"""

HTML_MISSIONS = """<!DOCTYPE html>
<html>
<head>
    <title>FlytBase Mission Control - Mission Planner</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b1120; color: #f8fafc; margin: 0; padding: 20px 20px 100px; }
        .card { background: #1e293b; padding: 24px; border-radius: 8px; border: 1px solid #334155; max-width: 600px; margin: 0 auto; }
        label { font-size: 13px; color: #94a3b8; display: block; margin-top: 12px; }
        input, select, textarea { width: 100%; padding: 10px; margin-top: 4px; border-radius: 4px; border: 1px solid #475569; background: #0f172a; color: white; box-sizing: border-box; }
        .btn-submit { margin-top: 20px; width: 100%; padding: 12px; background: #0284c7; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    __HEADER__
    <div class="card">
        <h3 style="margin-top: 0; color: #38bdf8;">📍 Plan Autonomous Flight Mission</h3>
        <form action="/mission_dispatch" method="POST">
            <label>Mission Code</label>
            <input type="text" name="mission_name" value="PERIMETER-SCAN-ALPHA" required>
            
            <label>Target Sector</label>
            <select name="sector">
                <option value="north">Sector North (Harbor)</option>
                <option value="east">Sector East (Substation)</option>
                <option value="south">Sector South (Perimeter)</option>
            </select>
            
            <label>Max Cruise Altitude (meters)</label>
            <input type="number" name="altitude" value="150" required>
            
            <label>Waypoint Coordinates (GeoJSON / CSV)</label>
            <textarea rows="3" name="waypoints">[{"lat": 37.7749, "lng": -122.4194}, {"lat": 37.7755, "lng": -122.4180}]</textarea>

            __SUBMIT_BUTTON__
        </form>
    </div>
    __FLOATING_BAR__
</body>
</html>
"""

HTML_FLEET = """<!DOCTYPE html>
<html>
<head>
    <title>FlytBase Mission Control - Fleet Status</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        html, body { max-width: 100%; overflow-x: hidden; margin: 0; padding: 15px 15px 100px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b1120; color: #f8fafc; }
        .table-container { max-width: 100%; width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; __CONTAINER_STYLE__ }
        table { min-width: 500px; width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; border: 1px solid #334155; }
        th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #334155; white-space: nowrap; }
        th { background: #0f172a; color: #94a3b8; font-size: 13px; text-transform: uppercase; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge-ready { background: #10b981; color: white; }
        .badge-charging { background: #eab308; color: black; }
        .btn-inspect { padding: 6px 12px; background: #334155; color: white; border: none; border-radius: 4px; cursor: pointer; __INSPECT_BTN_STYLE__ }
    </style>
</head>
<body>
    __HEADER__
    <h3 style="color: #38bdf8;">🛡️ Active Drone Fleet Registry</h3>
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Drone Unit</th>
                    <th>Model</th>
                    <th>Battery</th>
                    <th>Firmware</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Raven-X1</strong></td>
                    <td>DJI M300 RTK</td>
                    <td>88%</td>
                    <td>v4.2.1-stable</td>
                    <td><span class="badge badge-ready">Airborne</span></td>
                    <td><button class="btn-inspect">Telemetry View</button></td>
                </tr>
                <tr>
                    <td><strong>Falcon-09</strong></td>
                    <td>FlytBase Nest D60</td>
                    <td>95%</td>
                    <td>v4.2.1-stable</td>
                    <td><span class="badge badge-ready">Standby Dock</span></td>
                    <td><button class="btn-inspect">Telemetry View</button></td>
                </tr>
                <tr>
                    <td><strong>Eagle-V2</strong></td>
                    <td>Autel EVO Max</td>
                    <td>42%</td>
                    <td>v3.9.0</td>
                    <td><span class="badge badge-charging">Fast Charging</span></td>
                    <td><button class="btn-inspect">Telemetry View</button></td>
                </tr>
            </tbody>
        </table>
    </div>
    __FLOATING_BAR__
</body>
</html>
"""

HTML_DIAGNOSTICS = """<!DOCTYPE html>
<html>
<head>
    <title>FlytBase Mission Control - Hardware Diagnostics</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b1120; color: #f8fafc; margin: 0; padding: 20px 20px 100px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
        .sensor-card { background: #1e293b; padding: 18px; border-radius: 8px; border: 1px solid #334155; }
        .val { font-size: 22px; font-weight: bold; margin-top: 8px; color: #38bdf8; }
        .badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; float: right; }
        .badge-healthy { background: #10b981; color: white; }
        .badge-fault { background: #ef4444; color: white; }
    </style>
</head>
<body>
    __HEADER__
    <h3 style="color: #38bdf8;">🛰️ Hardware & Sensor Diagnostics</h3>
    <div class="grid">
        <div class="sensor-card">
            <div>IMU 1 (Triple Redundant) <span class="badge __IMU_BADGE_CLASS__">__IMU_BADGE_TEXT__</span></div>
            <div class="val">__IMU_VALUE__</div>
        </div>
        <div class="sensor-card">
            <div>RTK GNSS Positioning <span class="badge badge-healthy">Fixed (32 Sats)</span></div>
            <div class="val">Accuracy: ±1.2 cm</div>
        </div>
        <div class="sensor-card">
            <div>LiDAR Obstacle Radar <span class="badge badge-healthy">360° Clear</span></div>
            <div class="val">Detection: 45.0 m</div>
        </div>
        <div class="sensor-card">
            <div>ESC Motor Temperature <span class="badge badge-healthy">Nominal</span></div>
            <div class="val">42.8 °C</div>
        </div>
    </div>
    __FLOATING_BAR__
</body>
</html>
"""

HTML_SETTINGS = """<!DOCTYPE html>
<html>
<head>
    <title>FlytBase Mission Control - Restricted Settings</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b1120; color: #f8fafc; margin: 0; padding: 20px 20px 100px; }
        .card { background: #1e293b; padding: 24px; border-radius: 8px; border: 1px solid #ef4444; max-width: 600px; margin: 0 auto; }
        .warning { background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; padding: 12px; border-radius: 4px; color: #fca5a5; font-size: 13px; margin-bottom: 16px; }
    </style>
</head>
<body>
    __HEADER__
    <div class="card">
        <h3 style="margin-top: 0; color: #ef4444;">⚠️ Security & Flight Clearance Settings</h3>
        <div class="warning">Authorized Chief Flight Directors only. Changes directly affect BVLOS flight permissions.</div>
        <p>BVLOS Authorization Token: <code>FLYT-SEC-9941-K8</code></p>
        <p>Airspace Geofence Enforcement: <strong>Strict Class-B Airspace</strong></p>
        <p>Emergency Override Beacon: <strong>Armed</strong></p>
    </div>
    __FLOATING_BAR__
</body>
</html>
"""

HTML_STANDALONE_UI = """<!DOCTYPE html>
<html>
<head>
    <title>Tireless Hand - Autonomous Agent Cockpit HUD</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0b1120;
            color: #f8fafc;
            margin: 0;
            padding: 40px 20px 140px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .hero {
            text-align: center;
            max-width: 700px;
            margin-bottom: 30px;
        }
        .hero h1 {
            color: #38bdf8;
            font-size: 32px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
        }
        .hero p {
            color: #94a3b8;
            font-size: 16px;
            line-height: 1.5;
        }
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            width: 100%;
            max-width: 960px;
        }
        .hud-card {
            background: #1e293b;
            border: 1px solid #334155;
            padding: 20px;
            border-radius: 12px;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .hud-card:hover {
            transform: translateY(-2px);
            border-color: #38bdf8;
        }
        .hud-card h3 {
            margin-top: 0;
            color: #38bdf8;
            font-size: 17px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .hud-card p {
            font-size: 13px;
            color: #94a3b8;
            line-height: 1.4;
        }
        .hud-btn {
            display: inline-block;
            margin-top: 10px;
            padding: 8px 16px;
            background: #0284c7;
            color: white;
            border-radius: 6px;
            font-size: 12px;
            font-weight: bold;
            text-decoration: none;
            cursor: pointer;
            border: none;
        }
        .hud-btn:hover { background: #0369a1; }
    </style>
</head>
<body>
    <div class="hero">
        <h1>🦾 Tireless Hand UI</h1>
        <p>Autonomous Agentic UI & Reliability Tester with Self-Healing, Layout Auditors, and Video Proof Capture.</p>
    </div>

    <div class="cards-grid">
        <div class="hud-card">
            <h3>⚡ Full Quality Audit</h3>
            <p>Runs multi-viewport checks (Desktop, Tablet, Mobile), catches orphan forms, telemetry conflicts, and records .webm video proofs.</p>
            <button class="hud-btn" onclick="document.getElementById('tfb-url-input').value = 'http://localhost:8000/dashboard'; tfbRunAction('audit');">Audit Cockpit</button>
        </div>

        <div class="hud-card">
            <h3>🔍 Autonomous Exploration</h3>
            <p>Crawls live pages, extracts semantic accessibility tree, and persists discovered page graphs into SQLite.</p>
            <button class="hud-btn" style="background: #334155;" onclick="document.getElementById('tfb-url-input').value = 'http://localhost:8000/login'; tfbRunAction('explore');">Explore App</button>
        </div>

        <div class="hud-card">
            <h3>📊 12-Vector Benchmark</h3>
            <p>Validates precision, recall, accuracy, and F1-score across 12 clean & mutated drone scenarios.</p>
            <button class="hud-btn" style="background: #8b5cf6;" onclick="tfbRunAction('benchmark');">Run Benchmark</button>
        </div>

        <div class="hud-card">
            <h3>📄 Submission Reports</h3>
            <p>Inspect the latest interactive HTML report with embedded defect videos and reproduction steps.</p>
            <a href="/reports/submission.html" target="_blank" class="hud-btn" style="background: #0f172a; border: 1px solid #38bdf8; color: #38bdf8;">Open HTML Report →</a>
        </div>
    </div>

    __FLOATING_BAR__
</body>
</html>
"""


def _async_task_wrapper(coro):
    """Helper to run async coroutines in background threads."""
    asyncio.run(coro)


def run_background_audit(target_url: str, headless: bool):
    global AGENT_STATE
    AGENT_STATE["status"] = "running"
    AGENT_STATE["action"] = "audit"
    AGENT_STATE["message"] = f"Auditing {target_url} (headless={headless})..."

    async def _audit():
        global AGENT_STATE
        try:
            from tireless_hand.agent.auditor_runner import FullAuditRunner
            runner = FullAuditRunner(base_url=target_url, headless=headless, output_dir="./reports")
            if "suite" in target_url or "mutation" in target_url:
                suite_urls = [
                    "http://localhost:8000/login?mutation=orphan_form",
                    "http://localhost:8000/dashboard?mutation=telemetry_conflict&auth=1",
                    "http://localhost:8000/dashboard?mutation=responsive_clip",
                    "http://localhost:8000/dashboard?mutation=auth_bypass",
                ]
                await runner.run_suite_audit(suite_urls)
            else:
                await runner.run_full_audit()

            AGENT_STATE["status"] = "done"
            AGENT_STATE["message"] = f"Audit complete for {target_url}! Reports and videos saved."
            AGENT_STATE["last_result"] = {
                "target": target_url,
                "report": "/reports/submission.html",
                "markdown": "/reports/SUBMISSION.md",
                "video_dir": "/reports/videos/"
            }
        except Exception as e:
            AGENT_STATE["status"] = "done"
            AGENT_STATE["message"] = f"Audit encountered error: {e}"

    threading.Thread(target=_async_task_wrapper, args=(_audit(),), daemon=True).start()


def run_background_explore(target_url: str, headless: bool):
    global AGENT_STATE
    AGENT_STATE["status"] = "running"
    AGENT_STATE["action"] = "explore"
    AGENT_STATE["message"] = f"Exploring {target_url} (depth=2)..."

    async def _explore():
        global AGENT_STATE
        try:
            from tireless_hand.agent.orchestrator import TestOrchestrator
            from tireless_hand.browser.engine import BrowserConfig
            from tireless_hand.reasoning.llm_client import TieredLLMClient
            from tireless_hand.reasoning.bug_analyzer import BugAnalyzer

            config = BrowserConfig(headless=headless, slow_mo=50)
            llm = TieredLLMClient()
            analyzer = BugAnalyzer(llm)

            orchestrator = TestOrchestrator(
                llm_client=llm,
                bug_analyzer=analyzer,
                browser_config=config,
                memory_db_path="./memory/app_graph.db",
            )
            res = await orchestrator.explore(target_url, depth=2)
            AGENT_STATE["status"] = "done"
            AGENT_STATE["message"] = f"Exploration complete! Discovered {res.pages_discovered} pages and {res.elements_found} elements."
            AGENT_STATE["last_result"] = {
                "pages": res.pages_discovered,
                "elements": res.elements_found,
                "transitions": res.transitions_recorded
            }
        except Exception as e:
            AGENT_STATE["status"] = "done"
            AGENT_STATE["message"] = f"Exploration encountered error: {e}"

    threading.Thread(target=_async_task_wrapper, args=(_explore(),), daemon=True).start()


def run_background_benchmark():
    global AGENT_STATE
    AGENT_STATE["status"] = "running"
    AGENT_STATE["action"] = "benchmark"
    AGENT_STATE["message"] = "Running 12-vector evaluation benchmark suite..."

    async def _bench():
        global AGENT_STATE
        try:
            from benchmarks.run_benchmark import run_benchmark_suite
            res = await run_benchmark_suite()
            AGENT_STATE["status"] = "done"
            AGENT_STATE["message"] = f"Benchmark complete! Precision: {res['precision']*100:.1f}%, Recall: {res['recall']*100:.1f}%, F1: {res['f1_score']*100:.1f}%"
            AGENT_STATE["last_result"] = res
        except Exception as e:
            AGENT_STATE["status"] = "done"
            AGENT_STATE["message"] = f"Benchmark error: {e}"

    threading.Thread(target=_async_task_wrapper, args=(_bench(),), daemon=True).start()


class DemoServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        mutation = query.get("mutation", ["none"])[0]

        # Serve static reports & video files
        if path.startswith("/reports/"):
            rel_path = path.lstrip("/")
            file_path = Path(rel_path)
            if file_path.exists() and file_path.is_file():
                mime, _ = mimetypes.guess_type(str(file_path))
                self.send_response(200)
                self.send_header("Content-type", mime or "application/octet-stream")
                self.send_header("Content-Length", str(file_path.stat().st_size))
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_response(404)
                self.end_headers()
                return

        # Agent status endpoint
        if path == "/api/agent_status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(AGENT_STATE).encode("utf-8"))
            return

        # Dedicated Agent HUD
        if path == "/ui":
            html = HTML_STANDALONE_UI.replace("__FLOATING_BAR__", FLOATING_BAR_HTML)
            self._send_html(html)
            return

        # 1. Login Page
        if path in ("/", "/login"):
            submit_btn = '<button type="submit" id="btn-signin">Sign In to Fleet</button>'
            if mutation == "orphan_form":
                submit_btn = "<!-- Submit button stripped by mutation -->"

            html = (
                HTML_LOGIN
                .replace("__SUBMIT_BUTTON__", submit_btn)
                .replace("__FLOATING_BAR__", FLOATING_BAR_HTML)
            )
            self._send_html(html)
            return

        # Check authentication for protected routes
        auth_cookie = self.headers.get("Cookie", "")
        is_authorized = (
            "auth_token=" in auth_cookie
            or mutation in ("auth_bypass", "telemetry_conflict", "responsive_clip")
            or query.get("auth") == ["1"]
        )

        if not is_authorized and mutation != "auth_bypass":
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
            return

        # 2. Cockpit Dashboard
        if path == "/dashboard":
            status_class = "badge-offline" if mutation == "telemetry_conflict" else "badge-online"
            status_text = "Status: Offline" if mutation == "telemetry_conflict" else "Status: Online"
            action_style = "position: relative; width: 600px;" if mutation == "responsive_clip" else ""
            rth_style = "position: absolute; left: 520px;" if mutation == "responsive_clip" else ""

            html = (
                HTML_DASHBOARD
                .replace("__HEADER__", HTML_HEADER)
                .replace("__STATUS_BADGE_CLASS__", status_class)
                .replace("__STATUS_TEXT__", status_text)
                .replace("__ACTION_BAR_STYLE__", action_style)
                .replace("__RTH_BUTTON_STYLE__", rth_style)
                .replace("__FLOATING_BAR__", FLOATING_BAR_HTML)
            )
            self._send_html(html)
            return

        # 3. Mission Planner
        elif path == "/missions":
            submit_btn = '<button type="submit" class="btn-submit" id="btn-dispatch">Authorize & Launch Mission</button>'
            if mutation == "orphan_form":
                submit_btn = "<!-- Orphan Form: Missing Submit -->"

            html = (
                HTML_MISSIONS
                .replace("__HEADER__", HTML_HEADER)
                .replace("__SUBMIT_BUTTON__", submit_btn)
                .replace("__FLOATING_BAR__", FLOATING_BAR_HTML)
            )
            self._send_html(html)
            return

        # 4. Fleet Registry
        elif path == "/fleet":
            container_style = "overflow: visible; width: 800px; max-width: none;" if mutation == "responsive_clip" else ""
            btn_style = "margin-left: 200px;" if mutation == "responsive_clip" else ""

            html = (
                HTML_FLEET
                .replace("__HEADER__", HTML_HEADER)
                .replace("__CONTAINER_STYLE__", container_style)
                .replace("__INSPECT_BTN_STYLE__", btn_style)
                .replace("__FLOATING_BAR__", FLOATING_BAR_HTML)
            )
            self._send_html(html)
            return

        # 5. Diagnostics
        elif path == "/diagnostics":
            if mutation == "telemetry_conflict":
                imu_badge_class = "badge-fault"
                imu_badge_text = "Sensor: Disconnected"
                imu_val = "Sampling 500 Hz (Live)"
            else:
                imu_badge_class = "badge-healthy"
                imu_badge_text = "Operational"
                imu_val = "0.02° Pitch / 0.01° Roll"

            html = (
                HTML_DIAGNOSTICS
                .replace("__HEADER__", HTML_HEADER)
                .replace("__IMU_BADGE_CLASS__", imu_badge_class)
                .replace("__IMU_BADGE_TEXT__", imu_badge_text)
                .replace("__IMU_VALUE__", imu_val)
                .replace("__FLOATING_BAR__", FLOATING_BAR_HTML)
            )
            self._send_html(html)
            return

        # 6. Restricted Settings
        elif path == "/settings":
            html = (
                HTML_SETTINGS
                .replace("__HEADER__", HTML_HEADER)
                .replace("__FLOATING_BAR__", FLOATING_BAR_HTML)
            )
            self._send_html(html)
            return

        # Default fallback
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}

        if path == "/api/run_audit":
            target = payload.get("url", "http://localhost:8000/dashboard")
            headless = payload.get("headless", True)
            run_background_audit(target, headless)
            self._send_json({"ok": True, "message": f"Audit launched for {target}"})
            return

        elif path == "/api/run_explore":
            target = payload.get("url", "http://localhost:8000/login")
            headless = payload.get("headless", True)
            run_background_explore(target, headless)
            self._send_json({"ok": True, "message": f"Exploration launched for {target}"})
            return

        elif path == "/api/run_benchmark":
            run_background_benchmark()
            self._send_json({"ok": True, "message": "12-vector benchmark launched"})
            return

        elif path == "/login_submit":
            self.send_response(302)
            self.send_header("Set-Cookie", "auth_token=valid_pilot_session; Path=/")
            self.send_header("Location", "/dashboard")
            self.end_headers()
        elif path == "/mission_dispatch":
            self.send_response(302)
            self.send_header("Location", "/missions?status=dispatched&auth=1")
            self.end_headers()
        else:
            self.send_response(200)
            self.end_headers()

    def _send_html(self, html: str):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _send_json(self, data: dict):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_server(port: int = PORT):
    with ThreadingServer(("", port), DemoServerHandler) as httpd:
        print(f"[*] FlytBase Mission Control & Agent HUD running at http://localhost:{port}/ui")
        httpd.serve_forever()


if __name__ == "__main__":
    start_server()
