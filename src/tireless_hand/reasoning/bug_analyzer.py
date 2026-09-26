from dataclasses import dataclass
from typing import Optional
from .llm_client import TieredLLMClient, ChangeAnalysis

@dataclass
class BugAnalyzer:
    llm_client: TieredLLMClient

    async def analyze(self, baseline_state: str, current_state: str, change_description: Optional[str] = None) -> ChangeAnalysis:
        lower_current = current_state.lower()
        if any(keyword in lower_current for keyword in ["500 internal server error", "exception", "not found", "404 page"]):
            return ChangeAnalysis(
                verdict="BUG",
                confidence=0.9,
                reasoning="Error keywords detected in current state."
            )
        
        if "http status" in lower_current:
            import re
            match = re.search(r"http status:\s*([45]\d\d)", lower_current)
            if match:
                return ChangeAnalysis(
                    verdict="BUG",
                    confidence=1.0,
                    reasoning=f"HTTP Error status {match.group(1)} detected."
                )

        desc = change_description or "Unspecified change"
        return await self.llm_client.analyze_change(baseline_state, current_state, desc)
