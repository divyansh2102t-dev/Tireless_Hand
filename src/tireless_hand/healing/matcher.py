from dataclasses import dataclass
from typing import Optional, Any
from .fingerprint import Fingerprint, ElementFingerprinter

@dataclass
class MatchResult:
    element_id: str
    score: float
    strategy: str

class FuzzyMatcher:
    def __init__(self, min_threshold: float = 0.75):
        self.min_threshold = min_threshold
        self.fingerprinter = ElementFingerprinter()

    def _strategy_exact_match(self, target: Fingerprint, candidates: list[Fingerprint]) -> Optional[MatchResult]:
        for cand in candidates:
            if target.fingerprint_hash == cand.fingerprint_hash:
                return MatchResult(cand.element_id, 1.0, "exact_match")
        return None

    def _strategy_text_match(self, target: Fingerprint, candidates: list[Fingerprint]) -> Optional[MatchResult]:
        if not target.text_content:
            return None
        
        best_cand = None
        best_score = 0.0
        for cand in candidates:
            score = self.fingerprinter._text_similarity(target.text_content, cand.text_content)
            if score > best_score and score > 0.9:
                best_score = score
                best_cand = cand
        
        if best_cand:
            return MatchResult(best_cand.element_id, best_score, "text_match")
        return None

    def _strategy_role_text_match(self, target: Fingerprint, candidates: list[Fingerprint]) -> Optional[MatchResult]:
        if not target.role or not target.text_content:
            return None
            
        best_cand = None
        best_score = 0.0
        for cand in candidates:
            if target.role == cand.role:
                score = self.fingerprinter._text_similarity(target.text_content, cand.text_content)
                if score > best_score and score > 0.8:
                    best_score = score
                    best_cand = cand
        
        if best_cand:
            return MatchResult(best_cand.element_id, best_score, "role_text_match")
        return None

    def _strategy_context_match(self, target: Fingerprint, candidates: list[Fingerprint]) -> Optional[MatchResult]:
        if not target.parent_context:
            return None
            
        best_cand = None
        best_score = 0.0
        for cand in candidates:
            if target.parent_context == cand.parent_context:
                score = self.fingerprinter.compute_similarity(target, cand)
                if score > best_score and score > 0.7:
                    best_score = score
                    best_cand = cand
        
        if best_cand:
            return MatchResult(best_cand.element_id, best_score, "context_match")
        return None

    def _strategy_fuzzy_match(self, target: Fingerprint, candidates: list[Fingerprint]) -> Optional[MatchResult]:
        best_cand = None
        best_score = 0.0
        for cand in candidates:
            score = self.fingerprinter.compute_similarity(target, cand)
            if score > best_score and score >= self.min_threshold:
                best_score = score
                best_cand = cand
        
        if best_cand:
            return MatchResult(best_cand.element_id, best_score, "fuzzy_match")
        return None

    def find_best_match(self, target: Fingerprint, candidates: list[Fingerprint]) -> Optional[MatchResult]:
        strategies = [
            self._strategy_exact_match,
            self._strategy_text_match,
            self._strategy_role_text_match,
            self._strategy_context_match,
            self._strategy_fuzzy_match
        ]
        
        for strategy in strategies:
            result = strategy(target, candidates)
            if result:
                return result
                
        return None
