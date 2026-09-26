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
    issue_type: str  # "off_screen_horizontal", "horizontal_overflow", "clipped_text"
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
                await page.wait_for_timeout(700)

                # Check 1: Horizontal viewport overflow (with 10px tolerance)
                has_overflow = await page.evaluate(
                    """() => {
                        return document.documentElement.scrollWidth > (window.innerWidth + 10);
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
                    const interactive = Array.from(document.querySelectorAll('button, a.btn, a[role="button"], input[type="submit"], [role="button"]'));
                    const vpW = window.innerWidth;
                    const vpH = window.innerHeight;

                    for (const el of interactive) {
                        // Ignore injected HUD widgets or bottom floating bars
                        if (el.closest('#tireless-floating-bar-container, #tireless-floating-bar, [id^="tireless-floating"], [id^="tfb-"], #tfb-hud, .tfb-floating-panel, [data-agent-hud]')) continue;

                        const style = window.getComputedStyle(el);
                        
                        // Strict filter: Ignore hidden, off-canvas drawers, templates, sr-only or collapsed utility tags
                        const isHidden = (
                            style.display === 'none' ||
                            style.visibility === 'hidden' ||
                            style.opacity === '0' ||
                            el.hasAttribute('hidden') ||
                            el.getAttribute('aria-hidden') === 'true' ||
                            el.getAttribute('tabindex') === '-1' ||
                            el.classList.contains('sr-only') ||
                            el.classList.contains('visually-hidden') ||
                            el.offsetParent === null
                        );
                        if (isHidden) continue;

                        const rect = el.getBoundingClientRect();
                        const text = (el.innerText || el.getAttribute('aria-label') || el.value || el.title || '').trim();
                        
                        // Must be a meaningful interactive element with text or icons
                        if (!text && !el.querySelector('svg, img')) continue;

                        // Check if parent is an intentional horizontal scroll container (e.g. data table, code snippet, carousel)
                        let inScrollable = false;
                        let p = el.parentElement;
                        while (p && p !== document.body && p !== document.documentElement) {
                            const cs = window.getComputedStyle(p);
                            const ox = (cs.overflowX || cs.overflow || '').toLowerCase();
                            const tag = p.tagName.toUpperCase();
                            if (
                                ox.includes('auto') || 
                                ox.includes('scroll') || 
                                p.classList.contains('table-container') || 
                                tag === 'TABLE' || 
                                tag === 'TBODY' || 
                                tag === 'TR' || 
                                tag === 'TD' || 
                                tag === 'PRE'
                            ) {
                                inScrollable = true;
                                break;
                            }
                            p = p.parentElement;
                        }

                        // Check if actively pushed off-screen to the right
                        if (!inScrollable && (rect.left >= vpW || rect.right > vpW + 15)) {
                            results.push({
                                type: 'off_screen_horizontal',
                                text: text || el.tagName,
                                details: `Action element pushed off-screen at x=${Math.round(rect.left)}px (viewport width: ${vpW}px)`
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
