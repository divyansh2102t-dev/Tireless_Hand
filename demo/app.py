import http.server
import socketserver
import urllib.parse

PORT = 8000

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
</body>
</html>
"""

HTML_DASHBOARD = """<!DOCTYPE html>
<html>
<head>
    <title>FlytBase Mission Control - Fleet Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b1120; color: #f8fafc; margin: 0; padding: 20px; }
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
</body>
</html>
"""

HTML_MISSIONS = """<!DOCTYPE html>
<html>
<head>
    <title>FlytBase Mission Control - Mission Planner</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b1120; color: #f8fafc; margin: 0; padding: 20px; }
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
        html, body { max-width: 100%; overflow-x: hidden; margin: 0; padding: 15px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b1120; color: #f8fafc; }
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
</body>
</html>
"""

HTML_DIAGNOSTICS = """<!DOCTYPE html>
<html>
<head>
    <title>FlytBase Mission Control - Hardware Diagnostics</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b1120; color: #f8fafc; margin: 0; padding: 20px; }
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
</body>
</html>
"""

HTML_SETTINGS = """<!DOCTYPE html>
<html>
<head>
    <title>FlytBase Mission Control - Restricted Settings</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b1120; color: #f8fafc; margin: 0; padding: 20px; }
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
</body>
</html>
"""


class DemoServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        mutation = query.get("mutation", ["none"])[0]

        # 1. Login Page
        if path in ("/", "/login"):
            submit_btn = '<button type="submit" id="btn-signin">Sign In to Fleet</button>'
            if mutation == "orphan_form":
                submit_btn = "<!-- Submit button stripped by mutation -->"

            html = HTML_LOGIN.replace("__SUBMIT_BUTTON__", submit_btn)
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
            )
            self._send_html(html)
            return

        # 6. Restricted Settings
        elif path == "/settings":
            html = HTML_SETTINGS.replace("__HEADER__", HTML_HEADER)
            self._send_html(html)
            return

        # Default fallback
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/login_submit":
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


class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_server(port: int = PORT):
    with ThreadingServer(("", port), DemoServerHandler) as httpd:
        print(f"[*] FlytBase Mission Control Demo Server running at http://localhost:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    start_server()
