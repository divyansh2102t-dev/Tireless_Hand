from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import List, Any

class TestReporter:
    def __init__(self):
        self.console = Console()

    def print_summary(self, results: List[Any]):
        table = Table(title="Test Execution Summary")
        table.add_column("Flow Name", style="cyan")
        table.add_column("Passed", style="green")
        table.add_column("Steps", justify="right")

        for r in results:
            table.add_row(r.flow_name, "Yes" if r.passed else "No", str(len(r.steps)))
            
        self.console.print(table)

    def print_healing_stats(self, stats: dict):
        panel = Panel(
            f"Elements Healed: {stats.get('healed', 0)}\nHealing Success Rate: {stats.get('rate', '0%')}",
            title="Self-Healing Stats",
            style="blue"
        )
        self.console.print(panel)

    def generate_html_report(self, results: List[Any], output_path: str):
        html = "<html><body><h1>Test Report</h1></body></html>"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        self.console.print(f"[green]HTML report saved to {output_path}[/green]")
