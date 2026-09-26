"""Test Orchestrator - ties all components together.

This is the main brain of Tireless Hand. It coordinates:
- Browser automation (Playwright)
- DOM parsing (compact representation)
- Self-healing (fingerprint matching + LLM fallback)
- Persistent memory (SQLite app graph)
- Bug vs. feature analysis
- Test generation and execution
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

from ..browser.engine import BrowserEngine, BrowserConfig
from ..browser.dom_parser import DOMParser, ElementInfo
from ..browser.screenshot import ScreenshotManager
from ..healing.fingerprint import ElementFingerprinter, Fingerprint
from ..healing.matcher import FuzzyMatcher
from ..healing.resolver import SelfHealingResolver
from ..memory.store import MemoryStore
from ..memory.app_graph import AppGraph
from ..memory.baseline import BaselineManager
from ..reasoning.llm_client import TieredLLMClient
from ..reasoning.bug_analyzer import BugAnalyzer
from ..reasoning.prompts import SYSTEM_EXPLORER
from ..testing.generator import TestGenerator

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class ExplorationResult:
    """Result of exploring an application."""
    pages_discovered: int = 0
    elements_found: int = 0
    transitions_recorded: int = 0
    llm_calls_made: int = 0


@dataclass
class TestStep:
    """A single step in a test flow."""
    action: str  # navigate, click, fill, assert
    target: dict  # fingerprint or URL
    value: str = ""  # for fill/assert
    expected_result: str = ""


@dataclass
class Flow:
    """A test flow consisting of ordered steps."""
    name: str
    description: str = ""
    steps: list[TestStep] = field(default_factory=list)
    status: str = "pending"


@dataclass 
class StepResult:
    """Result of executing a single test step."""
    step: TestStep
    passed: bool
    healed: bool = False
    healing_strategy: str = ""
    error: str = ""
    screenshot_path: str = ""


@dataclass
class TestResult:
    """Result of running a complete test flow."""
    flow_name: str
    passed: bool
    step_results: list[StepResult] = field(default_factory=list)
    duration_sec: float = 0.0
    healed_count: int = 0


class TestOrchestrator:
    """Main orchestrator that coordinates all testing components."""

    def __init__(
        self,
        llm_client: Optional[TieredLLMClient] = None,
        bug_analyzer: Optional[BugAnalyzer] = None,
        browser_config: Optional[BrowserConfig] = None,
        memory_db_path: str = "./memory/app_graph.db",
        baseline_dir: str = "./memory/baselines",
    ):
        # Browser layer
        self.browser = BrowserEngine(browser_config or BrowserConfig())
        self.dom_parser = DOMParser()
        self.screenshot_mgr = ScreenshotManager()

        # Self-healing
        self.fingerprinter = ElementFingerprinter()
        self.matcher = FuzzyMatcher()
        self.resolver: Optional[SelfHealingResolver] = None  # initialized after browser starts

        # Memory
        self.memory = MemoryStore(db_path=memory_db_path)
        self.app_graph = AppGraph(self.memory)
        self.baseline_mgr = BaselineManager(store=self.memory)

        # AI reasoning
        self.llm = llm_client or TieredLLMClient()
        self.bug_analyzer = bug_analyzer or BugAnalyzer(self.llm)

        # Test generation
        self.test_generator = TestGenerator()

    async def _init(self):
        """Initialize async components."""
        await self.memory.init_db()
        await self.browser.start()
        self.resolver = SelfHealingResolver(
            matcher=self.matcher,
        )

    async def _cleanup(self):
        """Clean up resources."""
        await self.browser.stop()

    async def explore(self, url: str, depth: int = 3) -> ExplorationResult:
        """Explore an application and build the memory graph.

        Crawls the app starting from `url`, parsing each page's DOM,
        recording elements and transitions, and using the LLM to decide
        which elements to interact with next.
        """
        result = ExplorationResult()

        try:
            await self._init()

            visited: set[str] = set()
            to_visit: list[tuple[str, int]] = [(url, 0)]

            while to_visit:
                current_url, current_depth = to_visit.pop(0)

                if current_url in visited or current_depth > depth:
                    continue

                visited.add(current_url)
                console.print(f"[*] Exploring: [cyan]{current_url}[/cyan] (depth {current_depth}/{depth})")

                page = self.browser.get_page()
                if not page:
                    continue

                try:
                    await self.browser.goto(current_url)
                except Exception as e:
                    logger.warning(f"Failed to navigate to {current_url}: {e}")
                    continue

                compact_dom = await self.dom_parser.get_compact_dom(page)
                elements = await self.dom_parser.get_interactable_elements(page)
                title = await self.browser.current_title()
                dom_hash = hashlib.md5(compact_dom.encode()).hexdigest()

                is_known = await self.app_graph.is_known_page(current_url)

                # Save to memory
                await self.app_graph.record_page(
                    url=current_url,
                    title=title,
                    elements=[],
                    dom_hash=dom_hash,
                )
                result.pages_discovered += 1
                result.elements_found += len(elements)

                # Save baseline
                screenshot_path = f"./memory/baselines/{dom_hash}.png"
                try:
                    await self.browser.screenshot(screenshot_path)
                except Exception:
                    screenshot_path = ""

                # Print page info
                console.print(
                    f"  [green][+][/green] {title} ({current_url}) "
                    f"- {len(elements)} elements"
                    f"{' [dim](known)[/dim]' if is_known else ' [cyan](new)[/cyan]'}"
                )

                # Fingerprint all elements for memory
                for el in elements:
                    fp = self.fingerprinter.create_fingerprint(el)

                # If not too deep, ask LLM which elements to explore next
                if current_depth < depth and not is_known:
                    try:
                        response = await self.llm.query_fast(
                            f"Page DOM:\n{compact_dom}",
                            system=SYSTEM_EXPLORER,
                        )
                        result.llm_calls_made += 1

                        # Parse suggested actions
                        try:
                            json_str = response.strip()
                            if "```" in json_str:
                                json_str = json_str.split("```")[1]
                                if json_str.startswith("json"):
                                    json_str = json_str[4:]
                            suggestions = json.loads(json_str)
                        except (json.JSONDecodeError, IndexError):
                            suggestions = []

                        # Execute suggested actions to discover new pages
                        for suggestion in suggestions[:5]:
                            ref_id = suggestion.get("ref_id")
                            action = suggestion.get("action", "click")

                            if action == "click" and ref_id:
                                target_el = next(
                                    (e for e in elements if e.ref_id == ref_id),
                                    None,
                                )
                                if target_el and target_el.href:
                                    href = target_el.href
                                    if href.startswith("/"):
                                        from urllib.parse import urljoin
                                        href = urljoin(current_url, href)
                                    if not href.startswith(("javascript:", "mailto:", "#")):
                                        to_visit.append((href, current_depth + 1))
                                        await self.app_graph.record_transition(
                                            from_url=current_url,
                                            to_url=href,
                                            action="click",
                                            element=target_el.name or f"[{ref_id}]",
                                        )
                                        result.transitions_recorded += 1

                    except Exception as e:
                        logger.warning(f"LLM exploration failed: {e}")
                        # Fall back to exploring all links
                        for el in elements:
                            if el.role == "link" and el.href:
                                href = el.href
                                if href.startswith("/"):
                                    from urllib.parse import urljoin
                                    href = urljoin(current_url, href)
                                if not href.startswith(("javascript:", "mailto:", "#")):
                                    to_visit.append((href, current_depth + 1))

            # Print summary
            self._print_exploration_summary(result)

        finally:
            await self._cleanup()

        return result

    async def run_test(self, flow: Flow) -> TestResult:
        """Execute a single test flow with self-healing."""
        import time

        start = time.time()
        step_results: list[StepResult] = []
        healed = 0

        try:
            await self._init()

            for step in flow.steps:
                step_result = await self._execute_step(step)
                step_results.append(step_result)

                if step_result.healed:
                    healed += 1
                if not step_result.passed:
                    console.print(f"  [red][X][/red] Step failed: {step.action} -> {step_result.error}")
                    break
                else:
                    status = "[yellow]healed[/yellow]" if step_result.healed else "[green][OK][/green]"
                    console.print(f"  {status} {step.action} {step.target}")

        finally:
            await self._cleanup()

        duration = time.time() - start
        all_passed = all(r.passed for r in step_results)

        return TestResult(
            flow_name=flow.name,
            passed=all_passed,
            step_results=step_results,
            duration_sec=duration,
            healed_count=healed,
        )

    async def run_suite(self, flows: list[Flow]) -> list[TestResult]:
        """Run multiple test flows."""
        results = []
        for flow in flows:
            console.print(f"\n[bold]Running: {flow.name}[/bold]")
            result = await self.run_test(flow)
            results.append(result)
            status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
            console.print(f"  Result: {status} ({result.duration_sec:.1f}s, {result.healed_count} healed)")
        return results

    async def generate_tests(self, url: str) -> list[dict]:
        """Generate test specs from memory."""
        try:
            await self._init()

            # First explore if not already known
            is_known = await self.app_graph.is_known_page(url)
            if not is_known:
                console.print("[yellow]App not in memory, exploring first...[/yellow]")
                await self.explore(url, depth=2)

            specs = await self.test_generator.generate_from_exploration(self.app_graph)
            return specs

        finally:
            await self._cleanup()

    async def _execute_step(self, step: TestStep) -> StepResult:
        """Execute a single test step with self-healing."""
        page = self.browser.get_page()
        if not page:
            return StepResult(step=step, passed=False, error="No browser page")

        try:
            if step.action == "navigate":
                url = step.target.get("url", step.value)
                await self.browser.goto(url)
                return StepResult(step=step, passed=True)

            elif step.action == "click":
                selector = self._build_selector(step.target)
                try:
                    await page.click(selector, timeout=5000)
                    return StepResult(step=step, passed=True)
                except Exception:
                    healed_selector = await self._heal_selector(page, step.target)
                    if healed_selector:
                        await page.click(healed_selector, timeout=5000)
                        return StepResult(step=step, passed=True, healed=True, healing_strategy="fingerprint")
                    return StepResult(step=step, passed=False, error=f"Element not found: {step.target}")

            elif step.action == "fill":
                selector = self._build_selector(step.target)
                try:
                    await page.fill(selector, step.value, timeout=5000)
                    return StepResult(step=step, passed=True)
                except Exception:
                    healed_selector = await self._heal_selector(page, step.target)
                    if healed_selector:
                        await page.fill(healed_selector, step.value, timeout=5000)
                        return StepResult(step=step, passed=True, healed=True, healing_strategy="fingerprint")
                    return StepResult(step=step, passed=False, error=f"Element not found: {step.target}")

            elif step.action == "assert":
                return await self._execute_assertion(page, step)

            else:
                return StepResult(step=step, passed=False, error=f"Unknown action: {step.action}")

        except Exception as e:
            return StepResult(step=step, passed=False, error=str(e))

    def _build_selector(self, target: dict) -> str:
        """Build a Playwright selector from a target description."""
        if "selector" in target:
            return target["selector"]
        if "role" in target and "name" in target:
            return f"role={target['role']}[name=\"{target['name']}\"]"
        if "text" in target:
            return f"text={target['text']}"
        if "id" in target:
            return f"#{target['id']}"
        return str(target)

    async def _heal_selector(self, page, target: dict) -> Optional[str]:
        try:
            compact_dom = await self.dom_parser.get_compact_dom(page)
            elements = await self.dom_parser.get_interactable_elements(page)

            target_desc = target.get("name", target.get("text", str(target)))

            if "role" in target:
                role = target["role"]
                name = target.get("name", "")
                try:
                    locator = page.get_by_role(role, name=name)
                    if await locator.count() > 0:
                        return f"role={role}[name=\"{name}\"]"
                except Exception:
                    pass

            for el in elements:
                if target_desc.lower() in (el.name or "").lower():
                    return f"role={el.role}[name=\"{el.name}\"]"
                if target_desc.lower() in (el.text or "").lower():
                    return f"text={el.text}"

            ref_id = await self.llm.resolve_element(compact_dom, target_desc)
            try:
                rid = int(ref_id.strip())
                matched_el = next((e for e in elements if e.ref_id == rid), None)
                if matched_el:
                    if matched_el.id_attr:
                        return f"#{matched_el.id_attr}"
                    if matched_el.name:
                        return f"role={matched_el.role}[name=\"{matched_el.name}\"]"
            except (ValueError, StopIteration):
                pass

        except Exception as e:
            logger.warning(f"Self-healing failed: {e}")

        return None

    async def _execute_assertion(self, page, step: TestStep) -> StepResult:
        """Execute an assertion step."""
        target = step.target
        expected = step.expected_result or step.value

        try:
            if "page_title" in target:
                title = await page.title()
                if expected.startswith("contains "):
                    check_val = expected[9:].strip('"').strip("'")
                    passed = check_val.lower() in title.lower()
                else:
                    passed = title == expected
                if not passed:
                    return StepResult(step=step, passed=False, error=f"Title mismatch: got '{title}', expected '{expected}'")
                return StepResult(step=step, passed=True)

            elif "url" in target:
                current = page.url
                if expected.startswith("contains "):
                    check_val = expected[9:].strip('"').strip("'")
                    passed = check_val in current
                else:
                    passed = current == expected
                if not passed:
                    return StepResult(step=step, passed=False, error=f"URL mismatch: got '{current}', expected '{expected}'")
                return StepResult(step=step, passed=True)

            elif "text" in target:
                selector = self._build_selector(target)
                text = await page.text_content(selector)
                passed = expected in (text or "")
                if not passed:
                    return StepResult(step=step, passed=False, error=f"Text mismatch: got '{text}', expected '{expected}'")
                return StepResult(step=step, passed=True)

            else:
                return StepResult(step=step, passed=False, error=f"Unknown assertion target: {target}")

        except Exception as e:
            return StepResult(step=step, passed=False, error=str(e))

    def _print_exploration_summary(self, result: ExplorationResult):
        """Print a rich summary of the exploration."""
        table = Table(title="[*] Exploration Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Pages Discovered", str(result.pages_discovered))
        table.add_row("Elements Found", str(result.elements_found))
        table.add_row("Transitions Recorded", str(result.transitions_recorded))
        table.add_row("LLM Calls Made", str(result.llm_calls_made))
        table.add_row("LLM Stats", json.dumps(self.llm.stats, indent=2))

        console.print(table)
