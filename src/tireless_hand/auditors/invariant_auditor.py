import re
from dataclasses import dataclass
from typing import List, Optional
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


@dataclass
class InvariantIssue:
    issue_type: str  # "orphan_form", "telemetry_conflict", "unresponsive_control", "error_state"
    description: str
    details: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM"


class InvariantAuditor:
    """Audits functional and semantic invariant rules on web applications."""

    async def audit_page_invariants(self, page: Page) -> List[InvariantIssue]:
        issues: List[InvariantIssue] = []

        # Check 1: Orphan Form detection (Inputs present without any actionable submit button)
        orphan_form_script = r"""
        () => {
            const results = [];
            
            // Check form elements, ignoring injected agent HUD controls or search bars in header
            const inputElements = Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea, select'))
                .filter(i => !i.closest('#tireless-floating-bar-container, #tireless-floating-bar, [id^="tireless-floating"], [id^="tfb-"], #tfb-hud, .tfb-floating-panel, [data-agent-hud], header, nav'));

            if (inputElements.length >= 2) {
                const buttons = Array.from(document.querySelectorAll('button, input[type="submit"], [role="button"]'))
                    .filter(b => {
                        if (b.closest('#tireless-floating-bar-container, #tireless-floating-bar, [id^="tireless-floating"], [id^="tfb-"], #tfb-hud, .tfb-floating-panel, [data-agent-hud], header, nav')) return false;
                        const style = window.getComputedStyle(b);
                        return style.display !== 'none' && style.visibility !== 'hidden' && !b.disabled;
                    });
                
                const hasActionBtn = buttons.some(b => {
                    const txt = (b.innerText || b.value || b.getAttribute('aria-label') || '').toLowerCase();
                    return /submit|sign|login|continue|next|confirm|save|send|verify|register|enter|launch|dispatch|execute|create|start|apply|update/i.test(txt);
                });

                if (buttons.length === 0 || !hasActionBtn) {
                    results.push({
                        type: 'orphan_form',
                        inputs_count: inputElements.length,
                        inputs: inputElements.map(i => i.placeholder || i.name || i.type).join(', ')
                    });
                }
            }
            return results;
        }
        """
        try:
            orphan_results = await page.evaluate(orphan_form_script)
            for r in orphan_results:
                issues.append(
                    InvariantIssue(
                        issue_type="orphan_form",
                        description="Form contains input fields but missing actionable submit button",
                        details=f"Detected {r['inputs_count']} input fields ({r['inputs']}) with no enabled submit/sign-in button on screen.",
                        severity="CRITICAL",
                    )
                )
        except Exception as e:
            logger.debug(f"Orphan form check skipped: {e}")

        # Check 2: Semantic Telemetry & Status Conflict (e.g. Offline status with active flight data)
        conflict_script = r"""
        () => {
            const results = [];
            
            // Clone body or evaluate content ignoring floating HUD
            const hud = document.getElementById('tireless-floating-bar-container');
            let text = document.body.innerText.toLowerCase();
            if (hud && hud.innerText) {
                text = text.replace(hud.innerText.toLowerCase(), '');
            }

            // Pattern: Drone / Device status is OFFLINE or Disconnected
            const isOffline = /status[:\s]+offline|device[:\s]+disconnected|drone[:\s]+offline|sensor[:\s]+disconnected/i.test(text);

            // Conflicting active indicators
            const hasActiveTelemetry = /altitude[:\s]+[1-9]\d*|speed[:\s]+[1-9]\d*|armed[:\s]+true|motors[:\s]+running|streaming\s+live|sampling\s+\d+/i.test(text);
            const showsLiveBadge = Array.from(document.querySelectorAll('.badge, .status, span, div'))
                .some(el => {
                    if (el.closest('#tireless-floating-bar-container, #tireless-floating-bar, [id^="tireless-floating"], [id^="tfb-"], #tfb-hud, .tfb-floating-panel, [data-agent-hud]')) return false;
                    return el.innerText && /live|streaming|online|active|sampling/i.test(el.innerText) && window.getComputedStyle(el).display !== 'none';
                });

            if (isOffline && (hasActiveTelemetry || showsLiveBadge)) {
                results.push({
                    type: 'telemetry_conflict',
                    details: 'Status displays as Offline / Disconnected, but active telemetry (Altitude/Speed/Sensor stream) is simultaneously shown.'
                });
            }

            return results;
        }
        """
        try:
            conflict_results = await page.evaluate(conflict_script)
            for c in conflict_results:
                issues.append(
                    InvariantIssue(
                        issue_type="telemetry_conflict",
                        description="Contradictory state: Device marked Offline while active telemetry is displayed",
                        details=c["details"],
                        severity="CRITICAL",
                    )
                )
        except Exception as e:
            logger.debug(f"Conflict check skipped: {e}")

        return issues
