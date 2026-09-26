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
            const forms = Array.from(document.querySelectorAll('form, .form, [role="form"]'));
            const results = [];
            
            // Also check root if no explicit form tag exists
            const inputElements = Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea, select'));
            if (inputElements.length >= 2) {
                const buttons = Array.from(document.querySelectorAll('button, input[type="submit"], [role="button"]'))
                    .filter(b => {
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
            const text = document.body.innerText.toLowerCase();
            const results = [];

            // Pattern: Drone / Device status is OFFLINE or Disconnected
            const isOffline = /status[:\s]+offline|device[:\s]+disconnected|drone[:\s]+offline|sensor[:\s]+disconnected/i.test(text);

            // Conflicting active indicators
            const hasActiveTelemetry = /altitude[:\s]+[1-9]\d*|speed[:\s]+[1-9]\d*|armed[:\s]+true|motors[:\s]+running|streaming\s+live|sampling\s+\d+/i.test(text);
            const showsLiveBadge = Array.from(document.querySelectorAll('.badge, .status, span, div'))
                .some(el => el.innerText && /live|streaming|online|active|sampling/i.test(el.innerText) && window.getComputedStyle(el).display !== 'none');

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
                        severity="HIGH",
                    )
                )
        except Exception as e:
            logger.debug(f"Telemetry check skipped: {e}")

        # Check 3: Visible error alerts or crash banners
        error_script = """
        () => {
            const results = [];
            const errorElements = Array.from(document.querySelectorAll('.error, .alert-danger, [role="alert"], .crash-banner'));
            for (const el of errorElements) {
                const style = window.getComputedStyle(el);
                if (style.display !== 'none' && style.visibility !== 'hidden') {
                    const txt = el.innerText.trim();
                    if (txt.length > 5) {
                        results.push(txt);
                    }
                }
            }
            return results;
        }
        """
        try:
            error_banners = await page.evaluate(error_script)
            for err in error_banners:
                issues.append(
                    InvariantIssue(
                        issue_type="error_state",
                        description="Error banner or unhandled exception alert displayed to user",
                        details=f"Visible error message on screen: '{err[:100]}'",
                        severity="HIGH",
                    )
                )
        except Exception as e:
            logger.debug(f"Error banner check skipped: {e}")

        return issues
