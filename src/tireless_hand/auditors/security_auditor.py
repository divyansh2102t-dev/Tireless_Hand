from dataclasses import dataclass
from typing import List, Optional
from playwright.async_api import Browser, Page
from urllib.parse import urlparse, urljoin
import logging

logger = logging.getLogger(__name__)

COMMON_PROTECTED_PATHS = [
    "/dashboard",
    "/fleet",
    "/mission-control",
    "/admin",
    "/settings",
]


@dataclass
class SecurityIssue:
    url: str
    issue_type: str  # "auth_bypass", "missing_route_guard", "sensitive_data_exposure"
    description: str
    details: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM"


class SecurityAuditor:
    """Audits route protection and authentication boundaries."""

    async def audit_unauthenticated_access(
        self,
        browser: Browser,
        base_url: str,
        discovered_urls: Optional[List[str]] = None,
    ) -> List[SecurityIssue]:
        issues: List[SecurityIssue] = []
        parsed_base = urlparse(base_url)
        origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

        test_paths = set(COMMON_PROTECTED_PATHS)
        if parsed_base.path and parsed_base.path not in ("/", "/login", "/signin"):
            test_paths.add(parsed_base.path)

        if discovered_urls:
            for u in discovered_urls:
                p = urlparse(u).path
                if p and p not in ("/", "/login", "/signin", "/register", "/signup"):
                    test_paths.add(p)

        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        try:
            for path in list(test_paths)[:6]:
                target_url = urljoin(origin, path)
                try:
                    response = await page.goto(target_url, wait_until="domcontentloaded", timeout=3000)
                    if not response:
                        continue

                    current_url = page.url
                    page_title = await page.title()
                    status_code = response.status

                    # Check if the page stayed on the protected route and returned 200 without auth
                    is_login_redirect = any(
                        keyword in current_url.lower()
                        for keyword in ["login", "signin", "auth", "unauthorized", "access-denied"]
                    )

                    # Look for sensitive application content on the page
                    content = await page.content()
                    has_dashboard_elements = any(
                        marker in content.lower()
                        for marker in [
                            "mission control",
                            "drone fleet",
                            "telemetry",
                            "live feed",
                            "logout",
                            "sign out",
                            "user profile",
                            "battery level",
                            "rth",
                        ]
                    )

                    if status_code == 200 and not is_login_redirect and has_dashboard_elements:
                        issues.append(
                            SecurityIssue(
                                url=target_url,
                                issue_type="auth_bypass",
                                description=f"Unauthenticated user can access protected route '{path}' without sign-in",
                                details=(
                                    f"Direct GET request to {target_url} rendered protected page "
                                    f"(Title: '{page_title}', HTTP {status_code}) without redirecting to login."
                                ),
                                severity="CRITICAL",
                            )
                        )

                except Exception as e:
                    logger.debug(f"Route check for {target_url} skipped: {e}")

        finally:
            await context.close()

        return issues
