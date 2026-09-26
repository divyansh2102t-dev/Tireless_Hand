"""Tireless Hand CLI."""

import asyncio
import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

BANNER = "Tireless Hand CLI"

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Tireless Hand CLI"""
    console.print(BANNER, style="cyan")

@cli.command()
@click.argument("url")
@click.option("--depth", default=3, help="Max crawling depth from start URL")
@click.option("--headless/--no-headless", default=False, help="Run browser headless")
@click.option("--db", default="./memory/app_graph.db", help="Memory database path")
def explore(url: str, depth: int, headless: bool, db: str):
    async def _run():
        from .agent.orchestrator import TestOrchestrator
        from .browser.engine import BrowserConfig
        from .reasoning.llm_client import TieredLLMClient
        from .reasoning.bug_analyzer import BugAnalyzer

        config = BrowserConfig(headless=headless, slow_mo=50 if headless else 100)
        llm = TieredLLMClient()
        analyzer = BugAnalyzer(llm)

        orchestrator = TestOrchestrator(
            llm_client=llm,
            bug_analyzer=analyzer,
            browser_config=config,
            memory_db_path=db,
        )

        console.print(f"[bold cyan]Exploring[/bold cyan] {url} (depth={depth})")
        console.print(f"[dim]Memory: {db}[/dim]")
        console.print()

        result = await orchestrator.explore(url, depth=depth)

        console.print()
        console.print(Panel(
            f"[green]Exploration complete![/green]\n"
            f"Pages: {result.pages_discovered} | "
            f"Elements: {result.elements_found} | "
            f"Transitions: {result.transitions_recorded} | "
            f"LLM calls: {result.llm_calls_made}",
            title="[+] Done",
        ))

    asyncio.run(_run())

@cli.command()
@click.argument("url")
@click.option("--flow", help="Run a specific named flow")
@click.option("--spec", type=click.Path(exists=True), help="Path to YAML test spec")
@click.option("--heal/--no-heal", default=True, help="Enable self-healing")
@click.option("--headless/--no-headless", default=False, help="Run browser headless")
@click.option("--report", is_flag=True, help="Generate HTML report after run")
@click.option("--db", default="./memory/app_graph.db", help="Memory database path")
def test(url: str, flow: str, spec: str, heal: bool, headless: bool, report: bool, db: str):
    async def _run():
        from .agent.orchestrator import TestOrchestrator, Flow, TestStep
        from .browser.engine import BrowserConfig
        from .reasoning.llm_client import TieredLLMClient
        from .reasoning.bug_analyzer import BugAnalyzer
        from .reporting.reporter import TestReporter

        config = BrowserConfig(headless=headless, slow_mo=50 if headless else 100)
        llm = TieredLLMClient()
        analyzer = BugAnalyzer(llm)

        orchestrator = TestOrchestrator(
            llm_client=llm,
            bug_analyzer=analyzer,
            browser_config=config,
            memory_db_path=db,
        )

        console.print(f"[bold cyan]Testing[/bold cyan] {url}")
        console.print(f"[dim]Self-healing: {'enabled' if heal else 'disabled'}[/dim]")
        console.print()

        if spec:
            import yaml
            with open(spec) as f:
                spec_data = yaml.safe_load(f)
            
            steps = []
            for step_data in spec_data.get("steps", []):
                steps.append(TestStep(
                    action=step_data["action"],
                    target=step_data.get("target", {}),
                    value=step_data.get("value", ""),
                    expected_result=step_data.get("expected", ""),
                ))
            
            test_flow = Flow(
                name=spec_data.get("name", Path(spec).stem),
                description=spec_data.get("description", ""),
                steps=steps,
            )
            results = [await orchestrator.run_test(test_flow)]
        else:
            test_flow = Flow(
                name="basic-navigation",
                description=f"Basic navigation test for {url}",
                steps=[
                    TestStep(action="navigate", target={"url": url}),
                ],
            )
            results = [await orchestrator.run_test(test_flow)]

        reporter = TestReporter()
        reporter.print_summary(results)

        if report:
            report_path = f"./reports/report_{url.replace('://', '_').replace('/', '_')}.html"
            reporter.generate_html_report(results, report_path)
            console.print(f"[dim]Report saved to: {report_path}[/dim]")

    asyncio.run(_run())

@cli.command()
@click.argument("url")
@click.option("--output-dir", default="test_specs/", help="Output directory for test specs")
@click.option("--headless/--no-headless", default=False, help="Run browser headless")
@click.option("--db", default="./memory/app_graph.db", help="Memory database path")
def generate(url: str, output_dir: str, headless: bool, db: str):
    async def _run():
        from .agent.orchestrator import TestOrchestrator
        from .browser.engine import BrowserConfig
        from .reasoning.llm_client import TieredLLMClient
        from .reasoning.bug_analyzer import BugAnalyzer
        from .testing.generator import TestGenerator

        config = BrowserConfig(headless=headless, slow_mo=50)
        llm = TieredLLMClient()
        analyzer = BugAnalyzer(llm)

        orchestrator = TestOrchestrator(
            llm_client=llm,
            bug_analyzer=analyzer,
            browser_config=config,
            memory_db_path=db,
        )

        console.print(f"[bold cyan]Generating tests[/bold cyan] for {url}")
        console.print(f"[dim]Output: {output_dir}[/dim]")
        console.print()

        specs = await orchestrator.generate_tests(url)

        generator = TestGenerator()
        generator.write_test_specs(specs, output_dir)

        console.print(Panel(
            f"[green]Generated {len(specs)} test spec(s)[/green]\n"
            f"Output directory: {output_dir}",
            title="[+] Done",
        ))

    asyncio.run(_run())

@cli.command()
@click.option("--cost", is_flag=True, help="Show cost/inference metrics")
@click.option("--healing", is_flag=True, help="Show self-healing statistics")
@click.option("--coverage", is_flag=True, help="Show test coverage")
@click.option("--db", default="./memory/app_graph.db", help="Memory database path")
def report(cost: bool, healing: bool, coverage: bool, db: str):
    async def _run():
        from .memory.store import MemoryStore
        from .memory.app_graph import AppGraph

        memory = MemoryStore(db_path=db)
        await memory.init_db()
        graph = AppGraph(memory)

        if cost:
            console.print(Panel(
                "[green]Cost: $0.00[/green] (all inference is local via Ollama)\n"
                "No API keys used. No cloud bills.",
                title="💰 Cost Report",
            ))

        if healing:
            stats = await memory.get_healing_stats()
            table = Table(title="🔧 Self-Healing Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            for key, value in stats.items():
                table.add_row(str(key), str(value))
            console.print(table)

        if coverage:
            cov = await graph.get_exploration_coverage()
            table = Table(title="📊 Coverage Report")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            for key, value in cov.items():
                table.add_row(str(key), str(value))
            console.print(table)

        if not any([cost, healing, coverage]):
            console.print("[yellow]Use --cost, --healing, or --coverage to see specific reports[/yellow]")

    asyncio.run(_run())

@cli.command()
@click.option("--db", default="./memory/app_graph.db", help="Memory database path")
def status(db: str):
    async def _run():
        from .memory.store import MemoryStore
        from .memory.app_graph import AppGraph

        db_path = Path(db)
        if not db_path.exists():
            console.print("[yellow]No memory database found. Run 'tireless explore <url>' first.[/yellow]")
            return

        memory = MemoryStore(db_path=db)
        await memory.init_db()
        graph = AppGraph(memory)

        pages = await memory.get_known_pages()
        coverage = await graph.get_exploration_coverage()

        table = Table(title="[*] Memory Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Known Pages", str(coverage.get("total_pages", 0)))
        table.add_row("Total Elements", str(coverage.get("total_elements", 0)))
        table.add_row("Transitions", str(coverage.get("total_transitions", 0)))
        table.add_row("Database", str(db_path.absolute()))
        console.print(table)

        if pages:
            page_table = Table(title="[*] Known Pages")
            page_table.add_column("URL", style="blue")
            page_table.add_column("Title", style="white")
            page_table.add_column("Visits", style="green")
            for p in pages[:20]:
                page_table.add_row(p.url, p.title, str(p.visit_count))
            console.print(page_table)

    asyncio.run(_run())


@cli.command()
@click.argument("url", default="http://localhost:8000")
@click.option("--suite", is_flag=True, help="Run complete Level-1 mutation suite")
@click.option("--headless/--no-headless", default=True, help="Run browser headless")
@click.option("--output-dir", default="./reports", help="Output directory for reports and videos")
def audit(url: str, suite: bool, headless: bool, output_dir: str):
    """Run full Level-1 quality audit with video recording and generate submission document."""
    async def _run():
        from .agent.auditor_runner import FullAuditRunner

        runner = FullAuditRunner(base_url=url, headless=headless, output_dir=output_dir)
        if suite or url in ("all", "suite", "demo"):
            suite_urls = [
                "http://localhost:8000/login?mutation=orphan_form",
                "http://localhost:8000/dashboard?mutation=telemetry_conflict&auth=1",
                "http://localhost:8000/dashboard?mutation=responsive_clip",
                "http://localhost:8000/dashboard?mutation=auth_bypass",
            ]
            await runner.run_suite_audit(suite_urls)
        else:
            await runner.run_full_audit()

    asyncio.run(_run())


@cli.command()
@click.option("--port", default=8000, help="Local demo server port")
def demo(port: int):
    """Start the local FlytBase Mission Control demo app."""
    from demo.app import start_server
    start_server(port=port)


if __name__ == "__main__":
    cli()
