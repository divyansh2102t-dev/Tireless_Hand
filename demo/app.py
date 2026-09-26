import http.server
import socketserver
import urllib.parse

PORT = 8000

HTML_LOGIN = """<!DOCTYPE html>
<html>
<head>
    <title>FlytBase Mission Control - Login</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0b1120; color: #f8fafc; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 32px; border-radius: 8px; width: 340px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); }
        h2 { margin-top: 0; color: #38bdf8; }
        input { width: 100%; padding: 10px; margin: 8px 0 16px; border-radius: 4px; border: 1px solid #475569; background: #0f172a; color: white; box-sizing: border-box; }
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

            {SUBMIT_BUTTON}
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
        body {{ font-family: -apple-system, sans-serif; background: #0b1120; color: #f8fafc; margin: 0; padding: 20px; }}
        header {{ display: flex; justify-content: space-between; border-bottom: 1px solid #334155; padding-bottom: 12px; margin-bottom: 20px; }}
        .badge {{ padding: 4px 10px; border-radius: 4px; font-size: 13px; font-weight: bold; }}
        .badge-offline {{ background: #ef4444; color: white; }}
        .badge-online {{ background: #10b981; color: white; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }}
        .drone-card {{ background: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #334155; }}
        .telemetry-row {{ display: flex; justify-content: space-between; margin: 8px 0; border-bottom: 1px solid #283548; padding-bottom: 4px; }}
        .action-bar {{ margin-top: 16px; display: flex; gap: 10px; {ACTION_BAR_STYLE} }}
        .btn {{ padding: 10px 16px; border-radius: 4px; font-weight: bold; border: none; cursor: pointer; text-decoration: none; }}
        .btn-rth {{ background: #e11d48; color: white; {RTH_BUTTON_STYLE} }}
        .btn-land {{ background: #d97706; color: white; }}
    </style>
</head>
<body>
    <header>
        <h2>🚁 Drone Fleet Dispatch (Active)</h2>
        <div>Operator: <strong>Capt. Miller</strong></div>
    </header>

    <div class="grid">
        <div class="drone-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3>Drone Raven-X1</h3>
                <span class="badge {STATUS_BADGE_CLASS}">{STATUS_TEXT}</span>
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


class DemoServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        mutation = query.get("mutation", ["none"])[0]

        # Route 1: Login Page
        if path in ("/", "/login"):
            submit_btn = '<button type="submit" id="btn-signin">Sign In to Fleet</button>'
            if mutation == "orphan_form":
                # MUTATION 1: Removed submit button
                submit_btn = "<!-- Submit button was stripped by bug -->"

            html = HTML_LOGIN.replace("{SUBMIT_BUTTON}", submit_btn)
            self._send_html(html)
            return

        # Route 2: Protected Fleet Dashboard
        elif path == "/dashboard":
            # Check auth bypass mutation
            auth_cookie = self.headers.get("Cookie", "")
            if "auth_token=" not in auth_cookie and mutation != "auth_bypass":
                # Normal mode: redirect to login
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            # Telemetry Conflict mutation
            if mutation == "telemetry_conflict":
                status_class = "badge-offline"
                status_text = "Status: Offline"
            else:
                status_class = "badge-online"
                status_text = "Status: Online"

            # Responsive mutation (RTH button pushed off-screen at mobile width)
            if mutation == "responsive_clip":
                action_style = "position: relative; width: 600px;"
                rth_style = "position: absolute; left: 520px;"
            else:
                action_style = ""
                rth_style = ""

            html = HTML_DASHBOARD.format(
                STATUS_BADGE_CLASS=status_class,
                STATUS_TEXT=status_text,
                ACTION_BAR_STYLE=action_style,
                RTH_BUTTON_STYLE=rth_style,
            )
            self._send_html(html)
            return

        elif path == "/login_submit":
            # Issue auth cookie and redirect to dashboard
            self.send_response(302)
            self.send_header("Set-Cookie", "auth_token=valid_pilot_session; Path=/")
            self.send_header("Location", "/dashboard")
            self.end_headers()
            return

        else:
            self.send_error(404, "Page Not Found")

    def _send_html(self, html: str):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))


def start_server(port: int = PORT):
    with socketserver.TCPServer(("", port), DemoServerHandler) as httpd:
        print(f"[*] FlytBase Mission Control Demo Server running at http://localhost:{port}")
        print("Available mutation scenarios:")
        print(f"  - Baseline: http://localhost:{port}/login")
        print(f"  - Mutation 1 (Orphan Form): http://localhost:{port}/login?mutation=orphan_form")
        print(f"  - Mutation 2 (Telemetry Conflict): http://localhost:{port}/dashboard?mutation=telemetry_conflict&auth=1")
        print(f"  - Mutation 3 (Responsive Clipping): http://localhost:{port}/dashboard?mutation=responsive_clip")
        print(f"  - Mutation 4 (Auth Bypass): http://localhost:{port}/dashboard?mutation=auth_bypass")
        httpd.serve_forever()


if __name__ == "__main__":
    start_server()
