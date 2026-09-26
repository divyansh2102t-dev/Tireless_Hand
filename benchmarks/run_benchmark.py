"""Evaluation Benchmark Suite for Tireless Hand.
Measures Precision, Recall, Accuracy, and F1-Score across clean and mutated test cases.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from tireless_hand.browser.engine import BrowserEngine, BrowserConfig
from tireless_hand.auditors.responsive_auditor import ResponsiveAuditor
from tireless_hand.auditors.invariant_auditor import InvariantAuditor
from tireless_hand.auditors.security_auditor import SecurityAuditor
from tireless_hand.auditors.persistence_auditor import PersistenceAuditor

console = Console()


@dataclass
class TestCase:
    id: str
    name: str
    url: str
    category: str
    expected_bug: bool  # True = Positive (Buggy), False = Negative (Clean)
    target_auditor: str  # "responsive", "invariant", "security", "persistence"


TEST_MATRIX: List[TestCase] = [
    # --- NEGATIVE TEST CASES (Clean Pages - Expected No Bug / False Alarm Free) ---
    TestCase(
        id="TC-01",
        name="Clean Login Form",
        url="http://localhost:8000/login",
        category="Form Invariant",
        expected_bug=False,
        target_auditor="invariant",
    ),
    TestCase(
        id="TC-02",
        name="Clean Cockpit Telemetry",
        url="http://localhost:8000/dashboard?auth=1",
        category="Telemetry Invariant",
        expected_bug=False,
        target_auditor="invariant",
    ),
    TestCase(
        id="TC-03",
        name="Clean Mission Planner",
        url="http://localhost:8000/missions?auth=1",
        category="Form Invariant",
        expected_bug=False,
        target_auditor="invariant",
    ),
    TestCase(
        id="TC-04",
        name="Clean Fleet Responsive Layout",
        url="http://localhost:8000/fleet?auth=1",
        category="Responsive Layout",
        expected_bug=False,
        target_auditor="responsive",
    ),
    TestCase(
        id="TC-05",
        name="Clean Sensor Diagnostics",
        url="http://localhost:8000/diagnostics?auth=1",
        category="Telemetry Invariant",
        expected_bug=False,
        target_auditor="invariant",
    ),
    TestCase(
        id="TC-06",
        name="Enforced Route Guard on Settings",
        url="http://localhost:8000/settings",
        category="Auth Guard",
        expected_bug=False,
        target_auditor="security",
    ),

    # --- POSITIVE TEST CASES (Mutated Pages - Expected Bug Detection) ---
    TestCase(
        id="TC-07",
        name="Login Orphan Form (Stripped Submit)",
        url="http://localhost:8000/login?mutation=orphan_form",
        category="Form Invariant",
        expected_bug=True,
        target_auditor="invariant",
    ),
    TestCase(
        id="TC-08",
        name="Mission Planner Orphan Form",
        url="http://localhost:8000/missions?mutation=orphan_form&auth=1",
        category="Form Invariant",
        expected_bug=True,
        target_auditor="invariant",
    ),
    TestCase(
        id="TC-09",
        name="Drone Offline with Live Telemetry Conflict",
        url="http://localhost:8000/dashboard?mutation=telemetry_conflict&auth=1",
        category="Telemetry Invariant",
        expected_bug=True,
        target_auditor="invariant",
    ),
    TestCase(
        id="TC-10",
        name="Sensor Disconnected with Active Sampling",
        url="http://localhost:8000/diagnostics?mutation=telemetry_conflict&auth=1",
        category="Telemetry Invariant",
        expected_bug=True,
        target_auditor="invariant",
    ),
    TestCase(
        id="TC-11",
        name="Mobile Viewport Clipped RTH Button",
        url="http://localhost:8000/dashboard?mutation=responsive_clip&auth=1",
        category="Responsive Layout",
        expected_bug=True,
        target_auditor="responsive",
    ),
    TestCase(
        id="TC-12",
        name="Unauthenticated Access to Fleet Registry",
        url="http://localhost:8000/dashboard?mutation=auth_bypass",
        category="Auth Guard",
        expected_bug=True,
        target_auditor="security",
    ),
]


async def run_benchmark_suite() -> Dict[str, Any]:
    console.print(Panel("[bold cyan]Tireless Hand - Evaluation Benchmark Suite[/bold cyan]\nRunning full precision, recall, accuracy & F1 validation across clean and mutated test vectors...", title="[*] Benchmark Start"))

    engine = BrowserEngine(BrowserConfig(headless=True))
    await engine.start()

    responsive_auditor = ResponsiveAuditor()
    invariant_auditor = InvariantAuditor()
    security_auditor = SecurityAuditor()

    tp = 0
    fp = 0
    tn = 0
    fn = 0

    results = []
    start_time = time.time()

    for tc in TEST_MATRIX:
        console.print(f"[*] Testing [{tc.id}] {tc.name} ({tc.url})...", end=" ")
        detected_bugs = []

        if tc.target_auditor == "responsive":
            page = await engine.new_isolated_page(width=1280, height=720)
            issues = await responsive_auditor.audit_page(page, tc.url)
            detected_bugs = [i.details for i in issues]
            await page.close()
        elif tc.target_auditor == "invariant":
            page = await engine.new_isolated_page(width=1280, height=800)
            await page.goto(tc.url, wait_until="domcontentloaded")
            issues = await invariant_auditor.audit_page_invariants(page)
            detected_bugs = [i.description for i in issues]
            await page.close()
        elif tc.target_auditor == "security":
            issues = await security_auditor.audit_unauthenticated_access(engine._browser, tc.url)
            detected_bugs = [i.description for i in issues]

        has_bug = len(detected_bugs) > 0

        # Classification
        if tc.expected_bug and has_bug:
            outcome = "TP (True Positive)"
            tp += 1
            style = "green"
        elif not tc.expected_bug and not has_bug:
            outcome = "TN (True Negative)"
            tn += 1
            style = "green"
        elif not tc.expected_bug and has_bug:
            outcome = "FP (False Positive)"
            fp += 1
            style = "red"
        else:  # tc.expected_bug and not has_bug
            outcome = "FN (False Negative)"
            fn += 1
            style = "red"

        console.print(f"[{style}]{outcome}[/{style}]")

        results.append({
            "id": tc.id,
            "name": tc.name,
            "category": tc.category,
            "expected_bug": tc.expected_bug,
            "detected_bug": has_bug,
            "outcome": outcome,
            "details": detected_bugs,
        })

    await engine.stop()
    total_time = time.time() - start_time

    # Calculate standard evaluation metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 1.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    # Render Table
    table = Table(title="[*] Evaluation Benchmark Matrix")
    table.add_column("Test ID", style="cyan")
    table.add_column("Scenario Name", style="white")
    table.add_column("Category", style="yellow")
    table.add_column("Expected", style="blue")
    table.add_column("Detected", style="magenta")
    table.add_column("Classification", style="bold")

    for r in results:
        table.add_row(
            r["id"],
            r["name"],
            r["category"],
            "Bug" if r["expected_bug"] else "Clean",
            "Bug" if r["detected_bug"] else "Clean",
            f"[green]{r['outcome']}[/green]" if "T" in r["outcome"] else f"[red]{r['outcome']}[/red]"
        )

    console.print()
    console.print(table)

    # Metrics Summary Table
    metrics_table = Table(title="[*] Performance Metrics Summary")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Formula", style="dim")
    metrics_table.add_column("Value", style="bold green")

    metrics_table.add_row("True Positives (TP)", "Caught actual bugs", str(tp))
    metrics_table.add_row("True Negatives (TN)", "Passed clean pages without false alarms", str(tn))
    metrics_table.add_row("False Positives (FP)", "Clean pages flagged falsely", str(fp))
    metrics_table.add_row("False Negatives (FN)", "Mutations missed", str(fn))
    metrics_table.add_row("Precision", "TP / (TP + FP)", f"{precision * 100:.1f}% ({precision:.4f})")
    metrics_table.add_row("Recall", "TP / (TP + FN)", f"{recall * 100:.1f}% ({recall:.4f})")
    metrics_table.add_row("Accuracy", "(TP + TN) / Total", f"{accuracy * 100:.1f}% ({accuracy:.4f})")
    metrics_table.add_row("F1-Score", "2 * (P * R) / (P + R)", f"{f1_score * 100:.1f}% ({f1_score:.4f})")
    metrics_table.add_row("Benchmark Runtime", "Total Execution Time", f"{total_time:.2f}s")

    console.print()
    console.print(metrics_table)

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": len(TEST_MATRIX),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
        "f1_score": f1_score,
        "runtime_seconds": total_time,
        "cases": results,
    }

    Path("reports").mkdir(parents=True, exist_ok=True)
    with open("reports/benchmark_results.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    asyncio.run(run_benchmark_suite())
