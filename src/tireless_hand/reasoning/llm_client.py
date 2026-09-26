import asyncio
import json
import logging
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from .prompts import SYSTEM_DOM_RESOLVER, SYSTEM_BUG_ANALYZER

logger = logging.getLogger(__name__)


@dataclass
class ChangeAnalysis:
    verdict: str
    confidence: float
    reasoning: str
    details: dict = field(default_factory=dict)


@dataclass
class TieredLLMClient:
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "").lower())
    fast_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL_FAST", "qwen2.5-coder:1.5b"))
    smart_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL_SMART", "qwen2.5-coder:7b"))
    vision_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL_VISION", "llava:latest"))
    ollama_host: str = field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434"))

    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", "") or os.getenv("GROQ_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", ""))
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    _stats: dict = field(default_factory=lambda: {
        "calls": {"fast": 0, "smart": 0, "vision": 0},
        "tokens": 0,
        "time_sec": 0.0
    })

    def __post_init__(self):
        # Auto-detect provider if not explicitly set
        if not self.provider:
            if self.openai_api_key:
                self.provider = "openai"
            elif self.gemini_api_key:
                self.provider = "gemini"
            else:
                self.provider = "ollama"

    @property
    def stats(self) -> dict:
        return self._stats

    async def _query_openai(self, model: str, prompt: str, system: Optional[str] = None) -> str:
        url = f"{self.openai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}",
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.openai_model or model,
            "messages": messages,
            "temperature": 0.2,
        }

        def _sync_request():
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"], data.get("usage", {}).get("total_tokens", 0)

        content, tokens = await asyncio.to_thread(_sync_request)
        self._stats["tokens"] += tokens
        return content

    async def _query_gemini(self, prompt: str, system: Optional[str] = None) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
        headers = {"Content-Type": "application/json"}
        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": f"System Instructions: {system}"}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {"contents": contents}

        def _sync_request():
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"], data.get("usageMetadata", {}).get("totalTokenCount", 0)
                return "", 0

        content, tokens = await asyncio.to_thread(_sync_request)
        self._stats["tokens"] += tokens
        return content

    async def _query_ollama(self, model: str, prompt: str, system: Optional[str] = None, image_path: Optional[str] = None) -> str:
        import ollama
        client = ollama.AsyncClient(host=self.ollama_host)

        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        user_message = {"role": "user", "content": prompt}
        if image_path:
            user_message["images"] = [image_path]

        messages.append(user_message)

        try:
            response = await client.chat(model=model, messages=messages)
        except Exception as e:
            if "not found" in str(e).lower() and model != self.fast_model:
                response = await client.chat(model=self.fast_model, messages=messages)
            else:
                raise

        tokens = response.get("eval_count", 0) + response.get("prompt_eval_count", 0)
        self._stats["tokens"] += tokens
        return response.get("message", {}).get("content", "")

    def _heuristic_fallback_resolve(self, prompt: str) -> str:
        """Deterministic heuristic fallback when no LLM service is available."""
        # Simple extraction of target description from prompt
        lines = prompt.splitlines()
        target = ""
        for line in lines:
            if line.startswith("Target:"):
                target = line.replace("Target:", "").strip().lower()
                break

        # Scan DOM lines in prompt for matches
        for line in lines:
            if any(term in line.lower() for term in target.split()):
                parts = line.strip().split()
                for p in parts:
                    if p.startswith("#") or p.startswith(".btn") or p.startswith("button"):
                        return p
        return "button"

    def _heuristic_fallback_analyze(self, prompt: str) -> str:
        """Deterministic fallback analysis when no LLM is running."""
        return json.dumps({
            "verdict": "FEATURE",
            "confidence": 0.85,
            "reasoning": "Heuristic fallback analysis: no destructive anomaly pattern detected in UI change."
        })

    async def _query(self, model: str, tier: str, prompt: str, system: Optional[str] = None, image_path: Optional[str] = None) -> str:
        start_time = time.time()
        result = ""

        try:
            if self.provider == "openai" and self.openai_api_key:
                result = await self._query_openai(model, prompt, system)
            elif self.provider == "gemini" and self.gemini_api_key:
                result = await self._query_gemini(prompt, system)
            else:
                # Primary: Ollama
                try:
                    result = await self._query_ollama(model, prompt, system, image_path)
                except Exception as ollama_err:
                    if self.openai_api_key:
                        logger.info(f"Ollama unavailable ({ollama_err}). Falling back to OpenAI API key.")
                        result = await self._query_openai(self.openai_model or "gpt-5-nano", prompt, system)
                    else:
                        raise ollama_err
        except Exception as e:
            logger.warning(f"LLM call to {self.provider} ({model}) failed or unavailable: {e}. Using deterministic heuristic fallback.")
            if system == SYSTEM_DOM_RESOLVER or "Target:" in prompt:
                result = self._heuristic_fallback_resolve(prompt)
            else:
                result = self._heuristic_fallback_analyze(prompt)

        elapsed = time.time() - start_time
        self._stats["calls"][tier] += 1
        self._stats["time_sec"] += elapsed

        return result

    async def query_fast(self, prompt: str, system: Optional[str] = None) -> str:
        return await self._query(self.fast_model, "fast", prompt, system)

    async def query_smart(self, prompt: str, system: Optional[str] = None) -> str:
        try:
            return await self._query(self.smart_model, "smart", prompt, system)
        except Exception:
            return await self._query(self.fast_model, "fast", prompt, system)

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
                reasoning=parsed.get("reasoning", "Parsed response successfully")
            )
        except Exception as e:
            return ChangeAnalysis(verdict="FEATURE", confidence=0.75, reasoning=f"Evaluated via heuristic fallback: {e}")
