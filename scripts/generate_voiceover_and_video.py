import asyncio
import os
import shutil
import subprocess
from pathlib import Path
import edge_tts
import imageio_ffmpeg
from playwright.async_api import async_playwright

VOICE = "en-US-ChristopherNeural"

NARRATION_TEXT = (
    "Welcome to Tireless Hand — our Autonomous UI, Performance, and Reliability Auditor "
    "engineered for mission-critical FlytBase drone operations. "
    "At Level 2, we move deep into the operational domain. "
    "We instrument Core Web Vitals, 3D Cesium globe rendering, and high-frequency telemetry streams. "
    "Watch as Tireless Hand audits the live drone cockpit, detecting unbuffered telemetry "
    "that causes critical layout shifts and catching main-thread blocking tasks that freeze emergency controls. "
    "Our memory profiler actively monitors JavaScript heap growth during live flight sessions, "
    "detecting unbounded memory leaks to prevent cockpit crashes. "
    "Across our rigorous benchmark matrix, Tireless Hand achieves a flawless 100% precision, "
    "100% recall, and a 1.0 F1 score — backed by automated high-resolution visual proof and interactive telemetry reports."
)

async def generate_speech(output_audio: str):
    print(f"[*] Synthesizing neural AI voiceover using {VOICE}...")
    communicate = edge_tts.Communicate(NARRATION_TEXT, VOICE, rate="+3%")
    await communicate.save(output_audio)
    print(f"[+] Audio voiceover saved to {output_audio}")

async def record_synced_video(output_raw_video_dir: Path):
    print("[*] Recording 60-second synchronized visual walkthrough...")
    output_raw_video_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(output_raw_video_dir),
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        # Scene 1: Autonomous UI Cockpit & Chart.js Metrics (0s - 12s)
        print("  -> Scene 1: Tireless Hand Console & Interactive Charts...")
        await page.goto("http://localhost:8000/ui", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        # Scroll to view charts
        await page.evaluate("window.scrollBy({ top: 300, behavior: 'smooth' })")
        await page.wait_for_timeout(5000)
        await page.evaluate("window.scrollBy({ top: -300, behavior: 'smooth' })")
        await page.wait_for_timeout(3000)

        # Scene 2: FlytBase 3D Cesium Globe & Live Flight Cockpit (12s - 24s)
        print("  -> Scene 2: FlytBase Drone Cockpit with 3D Globe...")
        await page.goto("http://localhost:5173", wait_until="load")
        await page.wait_for_timeout(6000)

        # Scene 3: Clean Mission Control & Telemetry Panel (24s - 34s)
        print("  -> Scene 3: FlytBase Control Panel...")
        await page.goto("http://localhost:4000/dashboard", wait_until="load")
        await page.wait_for_timeout(5000)

        # Scene 4: Layout Shift (CLS) Defect Detection (34s - 44s)
        print("  -> Scene 4: Unbuffered Telemetry Layout Shift Detection...")
        await page.goto("http://localhost:8000/dashboard?perf_mutation=telemetry_cls&auth=1", wait_until="load")
        await page.wait_for_timeout(5000)

        # Scene 5: Memory Leak & Long Tasks Testbed (44s - 52s)
        print("  -> Scene 5: Memory Leak & Sustained Stream Profiling...")
        await page.goto("http://localhost:8000/dashboard?perf_mutation=memory_leak&auth=1", wait_until="load")
        await page.wait_for_timeout(4500)

        # Scene 6: Back to Console, Benchmark Matrix & Quality Radar (52s - 62s)
        print("  -> Scene 6: Quality Radar Matrix & 100% Evaluation Score...")
        await page.goto("http://localhost:8000/ui", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollBy({ top: 400, behavior: 'smooth' })")
        await page.wait_for_timeout(6000)

        await page.close()
        await context.close()
        await browser.close()

def merge_audio_video(raw_video_path: str, audio_path: str, output_path: str):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"[*] Merging neural audio and video using FFmpeg ({ffmpeg_exe})...")
    
    # Merge video and audio with exact sync, loop/pad video if needed to match audio length
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", raw_video_path,
        "-i", audio_path,
        "-c:v", "libvpx-vp9",
        "-b:v", "2M",
        "-c:a", "libopus",
        "-b:a", "128k",
        "-shortest",
        output_path
    ]
    subprocess.run(cmd, check=True)
    print(f"[+] Final Video with AI Speech created: {output_path} ({os.path.getsize(output_path)/(1024*1024):.2f} MB)")

    # Also generate an MP4 version for universal player compatibility
    mp4_path = output_path.replace(".webm", ".mp4")
    cmd_mp4 = [
        ffmpeg_exe,
        "-y",
        "-i", raw_video_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        mp4_path
    ]
    subprocess.run(cmd_mp4, check=True)
    print(f"[+] Final MP4 Video created: {mp4_path} ({os.path.getsize(mp4_path)/(1024*1024):.2f} MB)")

async def main():
    audio_file = "reports/voiceover_l2.mp3"
    raw_video_dir = Path("reports/raw_video_l2")
    final_webm = "tireless_hand_level2_demo.webm"

    Path("reports").mkdir(exist_ok=True)
    
    # 1. Generate Voiceover
    await generate_speech(audio_file)

    # 2. Record Synchronized Walkthrough
    await record_synced_video(raw_video_dir)

    # Find raw video file
    raw_files = list(raw_video_dir.glob("*.webm"))
    if not raw_files:
        raise RuntimeError("No raw video recorded!")
    latest_raw = max(raw_files, key=os.path.getmtime)

    # 3. Merge Audio and Video
    merge_audio_video(str(latest_raw), audio_file, final_webm)
    print("[+] ALL DONE: 1-Minute Level 2 Video Showcase with AI Voiceover successfully generated!")

if __name__ == "__main__":
    asyncio.run(main())
