import asyncio
import logging
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Playwright
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class BrowserConfig:
    headless: bool = False
    slow_mo: int = 100
    viewport_width: int = 1280
    viewport_height: int = 720
    timeout: int = 30000
    screenshot_dir: Path = field(default_factory=lambda: Path("./reports/screenshots"))

class BrowserEngine:
    """Wraps Playwright to provide browser automation capabilities."""
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        self.config.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo,
        )
        self._context = await self._browser.new_context(
            viewport={'width': self.config.viewport_width, 'height': self.config.viewport_height}
        )
        self._context.set_default_timeout(self.config.timeout)
        self._page = await self._context.new_page()

    async def stop(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
            
    def get_page(self) -> Optional[Page]:
        return self._page

    async def goto(self, url: str) -> None:
        if not self._page:
            raise RuntimeError("Browser not started")
        try:
            await self._page.goto(url, wait_until="networkidle")
        except Exception as e:
            logger.error(f"Navigation to {url} failed: {e}")

    async def click(self, selector: str) -> None:
        if not self._page:
            raise RuntimeError("Browser not started")
        await self._page.click(selector)

    async def fill(self, selector: str, text: str) -> None:
        if not self._page:
            raise RuntimeError("Browser not started")
        await self._page.fill(selector, text)

    async def screenshot(self, path: str | Path) -> None:
        if not self._page:
            raise RuntimeError("Browser not started")
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        await self._page.screenshot(path=str(filepath))

    async def current_url(self) -> str:
        if not self._page:
            raise RuntimeError("Browser not started")
        return self._page.url

    async def current_title(self) -> str:
        if not self._page:
            raise RuntimeError("Browser not started")
        return await self._page.title()
