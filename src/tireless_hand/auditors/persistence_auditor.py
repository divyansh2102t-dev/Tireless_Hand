from dataclasses import dataclass
from typing import List
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


@dataclass
class PersistenceIssue:
    issue_type: str  # "data_loss_on_refresh", "session_lost"
    description: str
    details: str
    severity: str  # "HIGH", "MEDIUM"


class PersistenceAuditor:
    """Audits client-side state resilience and refresh survival."""

    async def audit_refresh_resilience(self, page: Page) -> List[PersistenceIssue]:
        issues: List[PersistenceIssue] = []

        try:
            # Detect inputs that had values
            inputs = await page.evaluate(
                """() => {
                    const filled = [];
                    for (const inp of Array.from(document.querySelectorAll('input:not([type="password"]):not([type="hidden"]), textarea'))) {
                        if (inp.value && inp.value.length > 0) {
                            filled.push({ id: inp.id || inp.name || inp.type, val: inp.value });
                        }
                    }
                    return filled;
                }"""
            )

            if inputs:
                # Refresh page
                await page.reload(wait_until="domcontentloaded")
                await page.wait_for_timeout(400)

                # Check if draft content survived
                lost_count = await page.evaluate(
                    """(originalInputs) => {
                        let lost = 0;
                        for (const item of originalInputs) {
                            const current = document.getElementById(item.id) || document.querySelector(`[name="${item.id}"]`);
                            if (current && !current.value) {
                                lost++;
                            }
                        }
                        return lost;
                    }""",
                    inputs,
                )

                if lost_count > 0 and len(inputs) >= 2:
                    issues.append(
                        PersistenceIssue(
                            issue_type="data_loss_on_refresh",
                            description="Unsaved form input state is lost completely upon page refresh",
                            details=f"{lost_count} out of {len(inputs)} populated fields were cleared upon refresh without auto-draft recovery.",
                            severity="MEDIUM",
                        )
                    )
        except Exception as e:
            logger.debug(f"Persistence check skipped: {e}")

        return issues
