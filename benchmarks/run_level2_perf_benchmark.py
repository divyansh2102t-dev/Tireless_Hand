"""Level 2 Performance & Domain Testing Benchmark Suite for Tireless Hand
Evaluates Core Web Vitals (LCP, CLS), Long Tasks, Memory Leaks, Frame Rates, and Telemetry Jitter.
"""

import asyncio
import time
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path

from tireless_hand.browser.engine import BrowserEngine, BrowserConfig
from tireless_hand.auditors.performance_auditor import PerformanceAuditor, PerformanceReport

console = Console()

async def run_perf_benchmark():
    console.print(Panel(
        "[bold cyan]Tireless Hand — Level 2 Performance & Domain Testing Benchmark[/bold cyan]\n"
        "Auditing Core Web Vitals, Memory Stability, Frame Rates, and Real-Time Telemetry Jitter",
        title="[+] Level 2 Benchmark Initialized",
        border_style="cyan"
    ))

    config = BrowserConfig(headless=True, slow_mo=0, record_video=False)
    engine = BrowserEngine(config)
    await engine.start()

    auditor = PerformanceAuditor()

    test_targets = [
        {"name": "Clean Drone Cockpit Baseline", "url": "http://localhost:5173", "expected": "Clean"},
        {"name": "Clean FlytBase Control Panel", "url": "http://localhost:4000/dashboard", "expected": "Clean"},
        {"name": "Clean Mission Planner", "url": "http://localhost:8000/missions?auth=1", "expected": "Clean"},
        {"name": "Clean Diagnostics Stream", "url": "http://localhost:8000/diagnostics?auth=1", "expected": "Clean"},
        {"name": "Simulated Heavy Flight Map (High LCP)", "url": "http://localhost:8000/dashboard?perf_mutation=slow_lcp&auth=1", "expected": "Performance Defect"},
        {"name": "Unbuffered Telemetry Ingestion (High CLS)", "url": "http://localhost:8000/dashboard?perf_mutation=telemetry_cls&auth=1", "expected": "Performance Defect"},
        {"name": "Blocking Telemetry Parsing (Long Tasks)", "url": "http://localhost:8000/dashboard?perf_mutation=long_tasks&auth=1", "expected": "Performance Defect"},
        {"name": "Flight Session Memory Leak (Unbounded Heap)", "url": "http://localhost:8000/dashboard?perf_mutation=memory_leak&auth=1", "expected": "Performance Defect"},
    ]

    results = []
    tp, tn, fp, fn = 0, 0, 0, 0
    t0 = time.time()

    try:
        for idx, t in enumerate(test_targets, start=1):
            console.print(f"[cyan][*] Testing Vector {idx}/{len(test_targets)}:[/cyan] {t['name']}")
            context = await engine._browser.new_context(viewport={"width": 1280, "height": 720})
            page = await context.new_page()
            try:
                report = await auditor.audit_page_performance(page, t["url"], test_duration_sec=2.0)
            finally:
                await context.close()
            
            has_issues = len(report.issues) > 0
            detected = "Performance Defect" if has_issues else "Clean"
            expected = t["expected"]

            if expected == "Performance Defect" and detected == "Performance Defect":
                tp += 1
                classification = "[green]TP (True Positive)[/green]"
            elif expected == "Clean" and detected == "Clean":
                tn += 1
                classification = "[green]TN (True Negative)[/green]"
            elif expected == "Clean" and detected == "Performance Defect":
                fp += 1
                classification = "[red]FP (False Positive)[/red]"
            else:
                fn += 1
                classification = "[red]FN (False Negative)[/red]"

            results.append({
                "id": f"PERF-{idx:02d}",
                "name": t["name"],
                "url": t["url"],
                "fps": report.fps_average,
                "issues_count": len(report.issues),
                "expected": expected,
                "detected": detected,
                "classification": classification
            })

    finally:
        await engine.stop()

    total_time = round(time.time() - t0, 2)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    accuracy = (tp + tn) / len(test_targets) if len(test_targets) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0

    # Display Table
    table = Table(title="[Level 2] Performance Benchmark Results", border_style="cyan")
    table.add_column("Test ID", style="bold white")
    table.add_column("Scenario Name", style="cyan")
    table.add_column("Avg FPS", style="yellow")
    table.add_column("Defects", style="magenta")
    table.add_column("Expected", style="dim")
    table.add_column("Detected", style="dim")
    table.add_column("Classification", style="bold")

    for r in results:
        table.add_row(r["id"], r["name"], f"{r['fps']} FPS", str(r["issues_count"]), r["expected"], r["detected"], r["classification"])

    console.print(table)

    summary_panel = Panel(
        f"[bold green]Precision:[/bold green] {precision*100:.1f}% ({precision:.4f})\n"
        f"[bold green]Recall:[/bold green]    {recall*100:.1f}% ({recall:.4f})\n"
        f"[bold green]Accuracy:[/bold green]  {accuracy*100:.1f}% ({accuracy:.4f})\n"
        f"[bold green]F1-Score:[/bold green]  {f1*100:.1f}% ({f1:.4f})\n"
        f"[bold cyan]Runtime:[/bold cyan]   {total_time}s",
        title="[+] Performance Quality Metrics",
        border_style="green"
    )
    console.print(summary_panel)

    import json
    Path("reports").mkdir(exist_ok=True)
    with open("reports/level2_benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "precision": precision,
            "recall": recall,
            "accuracy": accuracy,
            "f1_score": f1,
            "runtime_seconds": total_time,
            "results": results
        }, f, indent=2)

    return {
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
        "f1_score": f1,
        "runtime_seconds": total_time,
        "results": results
    }

if __name__ == "__main__":
    asyncio.run(run_perf_benchmark())
