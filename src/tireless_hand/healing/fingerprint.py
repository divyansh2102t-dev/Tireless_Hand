import hashlib
import json
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Optional

@dataclass
class Fingerprint:
    element_id: str
    tag: str
    role: Optional[str] = None
    text_content: Optional[str] = None
    aria_label: Optional[str] = None
    id_attr: Optional[str] = None
    name_attr: Optional[str] = None
    placeholder: Optional[str] = None
    css_classes: list[str] = field(default_factory=list)
    position: Optional[tuple[float, float]] = None
    parent_context: Optional[str] = None
    fingerprint_hash: str = ""

    def __post_init__(self):
        if not self.fingerprint_hash:
            self._compute_hash()

    def _compute_hash(self):
        data = {
            "tag": self.tag,
            "role": self.role,
            "text": self.text_content,
            "aria_label": self.aria_label,
            "id": self.id_attr,
            "name": self.name_attr,
            "placeholder": self.placeholder,
            "classes": sorted(self.css_classes) if self.css_classes else []
        }
        hash_str = json.dumps(data, sort_keys=True)
        self.fingerprint_hash = hashlib.sha256(hash_str.encode()).hexdigest()

class ElementFingerprinter:
    WEIGHTS = {
        "aria_label": 0.95,
        "text_content": 0.90,
        "role": 0.85,
        "id_attr": 0.80,
        "name_attr": 0.75,
        "placeholder": 0.70,
        "tag": 0.60,
        "position": 0.50,
        "css_classes": 0.30
    }

    def create_fingerprint(self, element_info: dict[str, Any]) -> Fingerprint:
        return Fingerprint(
            element_id=element_info.get("element_id", ""),
            tag=element_info.get("tag", ""),
            role=element_info.get("role"),
            text_content=element_info.get("text_content"),
            aria_label=element_info.get("aria_label"),
            id_attr=element_info.get("id_attr"),
            name_attr=element_info.get("name_attr"),
            placeholder=element_info.get("placeholder"),
            css_classes=element_info.get("css_classes", []),
            position=element_info.get("position"),
            parent_context=element_info.get("parent_context")
        )

    def _text_similarity(self, s1: Optional[str], s2: Optional[str]) -> float:
        if s1 is None and s2 is None:
            return 1.0
        if not s1 or not s2:
            return 0.0
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def _list_similarity(self, l1: list[str], l2: list[str]) -> float:
        if not l1 and not l2:
            return 1.0
        if not l1 or not l2:
            return 0.0
        set1, set2 = set(l1), set(l2)
        if not set1 or not set2:
            return 0.0
        return len(set1 & set2) / len(set1 | set2)

    def compute_similarity(self, fp1: Fingerprint, fp2: Fingerprint) -> float:
        score = 0.0
        total_weight = 0.0

        for attr, weight in self.WEIGHTS.items():
            val1 = getattr(fp1, attr, None)
            val2 = getattr(fp2, attr, None)
            
            sim = 0.0
            if attr == "css_classes":
                sim = self._list_similarity(val1, val2)
            elif attr == "position":
                if val1 and val2:
                    dist = ((val1[0] - val2[0])**2 + (val1[1] - val2[1])**2)**0.5
                    sim = max(0.0, 1.0 - dist)
            else:
                sim = self._text_similarity(val1, val2)

            if val1 or val2:
                score += sim * weight
                total_weight += weight

        if total_weight == 0:
            return 0.0
        return score / total_weight
