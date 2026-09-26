import json
import time
from dataclasses import dataclass, field
import ollama
from .prompts import SYSTEM_DOM_RESOLVER, SYSTEM_BUG_ANALYZER

@dataclass
class ChangeAnalysis:
    verdict: str
    confidence: float
    reasoning: str
    details: dict = field(default_factory=dict)

@dataclass
class TieredLLMClient:
    fast_model: str = "qwen2.5-coder:1.5b"
    smart_model: str = "qwen2.5-coder:7b"
    vision_model: str = "llava:latest"
    
    _stats: dict = field(default_factory=lambda: {
        "calls": {"fast": 0, "smart": 0, "vision": 0},
        "tokens": 0,
        "time_sec": 0.0
    })

    @property
    def stats(self) -> dict:
        return self._stats

    async def _query(self, model: str, tier: str, prompt: str, system: str = None, image_path: str = None) -> str:
        start_time = time.time()
        client = ollama.AsyncClient()
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
            
        user_message = {"role": "user", "content": prompt}
        if image_path:
            user_message["images"] = [image_path]
            
        messages.append(user_message)

        try:
            response = await client.chat(model=model, messages=messages)
        except ollama.ResponseError as e:
            if "not found" in str(e).lower():
                raise RuntimeError(f"Model {model} not found. Please run 'ollama run {model}' to download it.") from e
            raise
        except Exception as e:
            if "not found" in str(e).lower() or "not found" in getattr(e, "message", "").lower():
                raise RuntimeError(f"Model {model} not found. Please run 'ollama run {model}' to download it.") from e
            raise

        elapsed = time.time() - start_time
        self._stats["calls"][tier] += 1
        tokens = response.get("eval_count", 0) + response.get("prompt_eval_count", 0)
        self._stats["tokens"] += tokens
        self._stats["time_sec"] += elapsed

        return response.get("message", {}).get("content", "")

    async def query_fast(self, prompt: str, system: str = None) -> str:
        return await self._query(self.fast_model, "fast", prompt, system)

    async def query_smart(self, prompt: str, system: str = None) -> str:
        return await self._query(self.smart_model, "smart", prompt, system)

    async def query_vision(self, prompt: str, image_path: str) -> str:
        return await self._query(self.vision_model, "vision", prompt, image_path=image_path)

    async def resolve_element(self, compact_dom: str, target_description: str) -> str:
        prompt = f"Target: {target_description}\nDOM:\n{compact_dom}"
        result = await self.query_fast(prompt, system=SYSTEM_DOM_RESOLVER)
        return result.strip()

    async def analyze_change(self, baseline_dom: str, current_dom: str, change_description: str) -> ChangeAnalysis:
        prompt = f"Baseline:\n{baseline_dom}\nCurrent:\n{current_dom}\nChange: {change_description}"
        result_json = await self.query_smart(prompt, system=SYSTEM_BUG_ANALYZER)
        
        try:
            clean_json = result_json.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            
            parsed = json.loads(clean_json.strip())
            return ChangeAnalysis(
                verdict=parsed.get("verdict", "UNKNOWN"),
                confidence=parsed.get("confidence", 0.0),
                reasoning=parsed.get("reasoning", "Parse error or omitted")
            )
        except Exception as e:
            return ChangeAnalysis(verdict="ERROR", confidence=0.0, reasoning=f"Failed to parse LLM response: {e}")
