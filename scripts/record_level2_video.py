import asyncio
import os
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

async def record_level2_video():
    video_dir = Path("./reports/videos_l2")
    video_dir.mkdir(parents=True, exist_ok=True)

    print("[*] Launching browser to record Level 2 Performance Testing Showcase...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        # Step 1: Open Agent UI Console
        print("[*] Navigating to Autonomous Agent HUD...")
        await page.goto("http://localhost:8000/ui", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Step 2: Show FlytBase Cockpit with Live 3D Globe
        print("[*] Inspecting FlytBase Drone Cockpit (Port 5173)...")
        await page.goto("http://localhost:5173", wait_until="load")
        await page.wait_for_timeout(3500)

        # Step 3: Show Performance Auditor In Action on Dashboard
        print("[*] Auditing Drone Dashboard...")
        await page.goto("http://localhost:8000/dashboard?auth=1", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Step 4: Show CLS and Layout Shift detection
        print("[*] Detecting Layout Shift (CLS) on Streaming Telemetry...")
        await page.goto("http://localhost:8000/dashboard?perf_mutation=telemetry_cls&auth=1", wait_until="load")
        await page.wait_for_timeout(2500)

        # Step 5: Show Mission Planner
        print("[*] Auditing Mission Planner...")
        await page.goto("http://localhost:8000/missions?auth=1", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Step 6: Return to Agent Console & View Benchmark Results
        print("[*] Returning to Agent Console & Final Report...")
        await page.goto("http://localhost:8000/ui", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        await page.close()
        await context.close()
        await browser.close()

    # Find the recorded video file and rename to tireless_hand_level2_demo.webm
    recorded_files = list(video_dir.glob("*.webm"))
    if recorded_files:
        latest = max(recorded_files, key=os.path.getmtime)
        dest = Path("./tireless_hand_level2_demo.webm")
        shutil.copy(str(latest), str(dest))
        print(f"[+] Level 2 Demonstration Video created: {dest.resolve()} ({dest.stat().st_size / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    asyncio.run(record_level2_video())
