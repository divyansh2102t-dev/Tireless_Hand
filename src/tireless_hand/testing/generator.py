import yaml
import os
from dataclasses import dataclass, asdict
from typing import List, Any

@dataclass
class TestSpec:
    name: str
    description: str
    steps: List[dict]

class TestGenerator:
    async def generate_from_exploration(self, app_graph: Any) -> List[TestSpec]:
        return [
            TestSpec(
                name="mock-flow",
                description="A mock test flow",
                steps=[{"action": "navigate", "target": "https://example.com"}]
            )
        ]

    async def generate_for_page(self, page_info: Any) -> TestSpec:
        return TestSpec(
            name="page-test",
            description="Test for a specific page",
            steps=[]
        )

    def write_test_specs(self, specs: List[TestSpec], output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        for spec in specs:
            path = os.path.join(output_dir, f"{spec.name}.yaml")
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(asdict(spec), f, sort_keys=False)
