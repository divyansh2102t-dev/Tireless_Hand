from dataclasses import dataclass
from typing import List, Optional
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)

VIEWPORTS = [
    {"name": "Desktop", "width": 1280, "height": 720},
    {"name": "Tablet", "width": 768, "height": 1024},
    {"name": "Mobile", "width": 375, "height": 667},
]


@dataclass
class ResponsiveIssue:
    viewport: str
    width: int
    height: int
    issue_type: str  # "off_screen", "horizontal_overflow", "hidden_cta", "clipped_text"
    element_description: str
    details: str
    severity: str  # "HIGH", "MEDIUM", "LOW"


class ResponsiveAuditor:
    """Audits a webpage across standard viewports to catch layout and mobile-readiness breakages."""

    async def audit_page(self, page: Page, url: str) -> List[ResponsiveIssue]:
        issues: List[ResponsiveIssue] = []

        for vp in VIEWPORTS:
            try:
                await page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(300)

                # Check 1: Horizontal viewport overflow
                has_overflow = await page.evaluate(
                    """() => {
                        return document.documentElement.scrollWidth > window.innerWidth;
                    }"""
                )
                if has_overflow:
                    issues.append(
                        ResponsiveIssue(
                            viewport=vp["name"],
                            width=vp["width"],
                            height=vp["height"],
                            issue_type="horizontal_overflow",
                            element_description="Page Body / Root Container",
                            details=f"Horizontal scroll detected ({vp['name']} width {vp['width']}px). Content exceeds viewport width.",
                            severity="HIGH" if vp["name"] == "Mobile" else "MEDIUM",
                        )
                    )

                # Check 2: Action buttons pushed outside visible area or clipped
                script_check_elements = """
                () => {
                    const results = [];
                    const interactive = Array.from(document.querySelectorAll('button, a.btn, input[type="submit"], [role="button"]'));
                    const vpW = window.innerWidth;
                    const vpH = window.innerHeight;

                    for (const el of interactive) {
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden') continue;

                        const rect = el.getBoundingClientRect();
                        const text = (el.innerText || el.getAttribute('aria-label') || el.value || '').trim();
                        
                        // Check if pushed off-screen to the right
                        if (rect.left >= vpW || rect.right > vpW + 10) {
                            results.push({
                                type: 'off_screen_horizontal',
                                text: text || el.tagName,
                                details: `Element positioned at x=${Math.round(rect.left)}px, beyond screen width (${vpW}px)`
                            });
                        }
                        // Check if element has zero clickable area
                        else if (rect.width <= 0 || rect.height <= 0) {
                            results.push({
                                type: 'zero_dimension',
                                text: text || el.tagName,
                                details: 'Interactive element collapsed to 0 width/height'
                            });
                        }
                    }
                    return results;
                }
                """
                element_issues = await page.evaluate(script_check_elements)
                for item in element_issues:
                    issues.append(
                        ResponsiveIssue(
                            viewport=vp["name"],
                            width=vp["width"],
                            height=vp["height"],
                            issue_type=item["type"],
                            element_description=item["text"][:60],
                            details=f"[{vp['name']}] {item['details']}",
                            severity="HIGH",
                        )
                    )

            except Exception as e:
                logger.warning(f"Error auditing viewport {vp['name']}: {e}")

        # Reset viewport to standard desktop
        await page.set_viewport_size({"width": 1280, "height": 720})
        return issues
