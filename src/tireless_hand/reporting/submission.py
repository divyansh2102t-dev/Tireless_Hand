import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import json


@dataclass
class ScenarioReport:
    id: int
    title: str
    category: str  # "Visual UI", "Responsive UI", "Functional UI", "Security", "Telemetry", etc.
    description: str
    approach: str
    video_path: str
    steps_to_reproduce: List[str]
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    status: str = "FAILED"  # Bug detected (FAILED = product bug caught)
    evidence: str = ""


class SubmissionGenerator:
    """Generates evaluation documents matching the hackathon submission specification."""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_markdown(
        self,
        system_design: str,
        scenarios: List[ScenarioReport],
        filename: str = "SUBMISSION.md",
    ) -> str:
        filepath = self.output_dir / filename

        lines = [
            "# Software Factory Series — The Tireless Hand Challenge",
            "## Autonomous Agentic UI & Reliability Evaluation Document",
            "",
            "---",
            "",
            "## 1. System Design",
            "",
            system_design.strip(),
            "",
            "---",
            "",
            "## 2. Evaluation Scenarios",
            "",
        ]

        for s in scenarios:
            lines.extend(
                [
                    f"### Scenario {s.id}: {s.title}",
                    f"- **Category**: `{s.category}`",
                    f"- **Severity**: **{s.severity}**",
                    f"- **Result**: `{s.status}` (Issue caught by autonomous agent)",
                    f"- **Video Recording**: [`{Path(s.video_path).name}`]({s.video_path})",
                    "",
                    "#### Description",
                    s.description.strip(),
                    "",
                    "#### Approach",
                    s.approach.strip(),
                    "",
                    "#### Steps to Reproduce",
                ]
            )
            for idx, step in enumerate(s.steps_to_reproduce, start=1):
                lines.append(f"{idx}. {step}")

            if s.evidence:
                lines.extend(["", "#### Evidence & Artifacts", s.evidence.strip()])

            lines.append("\n---\n")

        content = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return str(filepath)

    def generate_html(
        self,
        system_design: str,
        scenarios: List[ScenarioReport],
        filename: str = "submission.html",
    ) -> str:
        filepath = self.output_dir / filename

        scenario_cards = ""
        for s in scenarios:
            steps_html = "".join(f"<li>{step}</li>" for step in s.steps_to_reproduce)
            video_rel = os.path.relpath(s.video_path, start=str(self.output_dir)) if os.path.exists(s.video_path) else s.video_path
            
            badge_color = "#e53e3e" if s.severity in ("CRITICAL", "HIGH") else "#dd6b20"
            
            scenario_cards += f"""
            <div class="card">
                <div class="card-header">
                    <span class="badge" style="background:{badge_color}">{s.severity}</span>
                    <span class="category-tag">{s.category}</span>
                    <h3>Scenario {s.id}: {s.title}</h3>
                </div>
                <div class="card-body">
                    <p><strong>Description:</strong> {s.description}</p>
                    <p><strong>Approach:</strong> {s.approach}</p>
                    <div class="steps-box">
                        <strong>Steps to Reproduce:</strong>
                        <ol>{steps_html}</ol>
                    </div>
                    {f'<div class="evidence-box"><strong>Evidence:</strong> {s.evidence}</div>' if s.evidence else ''}
                    <div class="video-box">
                        <p><strong>Screen Recording Evidence:</strong> <a href="{video_rel}" target="_blank">{Path(s.video_path).name}</a></p>
                        <video controls width="100%" style="max-height: 400px; border-radius: 6px; background: #000;">
                            <source src="{video_rel}" type="video/webm">
                            Your browser does not support HTML5 video.
                        </video>
                    </div>
                </div>
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Tireless Hand — Hackathon Evaluation Document</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; line-height: 1.6; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        h1, h2, h3 {{ color: #38bdf8; }}
        .section {{ background: #1e293b; border-radius: 8px; padding: 24px; margin-bottom: 24px; border: 1px solid #334155; }}
        .card {{ background: #1e293b; border-radius: 8px; margin-bottom: 20px; border: 1px solid #334155; overflow: hidden; }}
        .card-header {{ padding: 16px 20px; background: #0f172a; border-bottom: 1px solid #334155; }}
        .card-body {{ padding: 20px; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; color: #fff; margin-right: 8px; }}
        .category-tag {{ background: #334155; padding: 4px 8px; border-radius: 4px; font-size: 12px; color: #94a3b8; }}
        .steps-box {{ background: #0f172a; padding: 12px 20px; border-radius: 6px; margin: 12px 0; border-left: 3px solid #38bdf8; }}
        .evidence-box {{ background: #2d1515; padding: 10px 14px; border-radius: 6px; margin: 12px 0; border-left: 3px solid #ef4444; }}
        .video-box {{ margin-top: 16px; background: #0f172a; padding: 12px; border-radius: 6px; }}
        a {{ color: #38bdf8; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Tireless Hand — Evaluation Document</h1>
        <p>Autonomous UI testing system running on deterministic DOM matching, local tiered models, and multi-vector quality auditors.</p>
        
        <div class="section">
            <h2>1. System Design</h2>
            <pre style="white-space: pre-wrap; font-family: inherit; color: #cbd5e1;">{system_design}</pre>
        </div>

        <h2>2. Discovered Scenarios & Reproducible Evidence</h2>
        {scenario_cards}
    </div>
</body>
</html>
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(filepath)
