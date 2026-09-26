import uuid
import difflib
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timezone
import imagehash
from PIL import Image

from .store import MemoryStore, BaselineRecord

@dataclass
class ChangeReport:
    added_elements: List[str]
    removed_elements: List[str]
    changed_elements: List[str]
    visual_similarity: float
    is_significant_change: bool

@dataclass
class Baseline:
    url: str
    dom_snapshot: str
    screenshot_hash: str
    created: datetime

class BaselineManager:
    def __init__(self, store: MemoryStore, visual_threshold: float = 0.9, dom_threshold: float = 0.8):
        self.store = store
        self.visual_threshold = visual_threshold
        self.dom_threshold = dom_threshold

    async def save_baseline(self, url: str, compact_dom: str, screenshot_path: str) -> None:
        page = await self.store.get_page(url)
        if not page:
            raise ValueError(f"Cannot save baseline for unknown page: {url}")
            
        try:
            img = Image.open(screenshot_path)
            phash = str(imagehash.phash(img))
        except Exception:
            phash = ""

        await self.store.save_baseline(
            page_id=page.id,
            dom_snapshot=compact_dom,
            screenshot_hash=phash
        )

    async def get_baseline(self, url: str) -> Optional[Baseline]:
        page = await self.store.get_page(url)
        if not page:
            return None
            
        record = await self.store.get_baseline(page.id)
        if not record:
            return None
            
        return Baseline(
            url=url,
            dom_snapshot=record.dom_snapshot,
            screenshot_hash=record.screenshot_hash,
            created=record.created
        )

    async def compare_with_baseline(self, url: str, current_dom: str, current_screenshot: str) -> ChangeReport:
        baseline = await self.get_baseline(url)
        if not baseline:
            return ChangeReport([], [], [], 0.0, False)
            
        diff = difflib.ndiff(baseline.dom_snapshot.splitlines(), current_dom.splitlines())
        added = []
        removed = []
        for line in diff:
            if line.startswith('+ '):
                added.append(line[2:])
            elif line.startswith('- '):
                removed.append(line[2:])
                
        try:
            img = Image.open(current_screenshot)
            current_hash = imagehash.phash(img)
            base_hash = imagehash.hex_to_hash(baseline.screenshot_hash)
            
            hash_diff = current_hash - base_hash
            visual_similarity = max(0.0, 1.0 - (hash_diff / 64.0))
        except Exception:
            visual_similarity = 1.0

        is_significant = (visual_similarity < self.visual_threshold) or (len(added) + len(removed) > 10)
        
        return ChangeReport(
            added_elements=added,
            removed_elements=removed,
            changed_elements=[],
            visual_similarity=visual_similarity,
            is_significant_change=is_significant
        )
