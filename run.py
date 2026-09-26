"""Tireless Hand - One-Command Universal Launcher
Launches the demo server, audit testbed, and interactive floating HUD in the browser.
"""

import sys
import webbrowser
from pathlib import Path

# Add src to pythonpath
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    print("=" * 60)
    print("  🚀 TIRELESS HAND — AUTONOMOUS QA & AUDITING AGENT")
    print("=" * 60)
    print("  [*] Launching Unified Server & Interactive HUD...")
    print("  [*] Standalone HUD URL:  http://localhost:8000/ui")
    print("  [*] Live Demo Dashboard: http://localhost:8000/dashboard")
    print("  [*] Injected Defect Lab: http://localhost:8000/broken")
    print("=" * 60)
    print("  💡 Tip: You can trigger audits, exploration, and benchmarks")
    print("     directly from the floating top bar without touching the terminal!")
    print("=" * 60)

    try:
        webbrowser.open("http://localhost:8000/ui")
    except Exception:
        pass

    from demo.app import start_server
    start_server(port=8000)

if __name__ == "__main__":
    main()
