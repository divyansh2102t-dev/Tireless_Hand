import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Response,
    async_playwright,
)

logger = logging.getLogger(__name__)


@dataclass
class NetworkError:
    url: str
    status: int
    status_text: str
    method: str


@dataclass
class BrowserConfig:
    headless: bool = False
    slow_mo: int = 50
    viewport_width: int = 1280
    viewport_height: int = 720
    timeout: int = 30000
    record_video: bool = True
    screenshot_dir: Path = field(default_factory=lambda: Path("./reports/screenshots"))
    video_dir: Path = field(default_factory=lambda: Path("./reports/videos"))


class BrowserEngine:
    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        self.console_errors: List[str] = []
        self.page_errors: List[str] = []
        self.network_errors: List[NetworkError] = []

        self.config.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.config.video_dir.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self, record_video: Optional[bool] = None) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo,
        )

        should_record = self.config.record_video if record_video is None else record_video
        context_args: dict = {
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            }
        }
        if should_record:
            context_args["record_video_dir"] = str(self.config.video_dir)
            context_args["record_video_size"] = {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            }

        self._context = await self._browser.new_context(**context_args)
        self._context.set_default_timeout(self.config.timeout)
        self._page = await self._context.new_page()
        self._attach_listeners(self._page)

    def _attach_listeners(self, page: Page) -> None:
        page.on("console", lambda msg: self.console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: self.page_errors.append(str(err)))
        page.on("response", self._handle_response)

    def _handle_response(self, response: Response) -> None:
        if response.status >= 400:
            self.network_errors.append(
                NetworkError(
                    url=response.url,
                    status=response.status,
                    status_text=response.status_text,
                    method=response.request.method,
                )
            )

    async def new_isolated_page(self, width: int = 1280, height: int = 720) -> Page:
        """Create a fresh isolated context without cookies or stored state (for auth testing)."""
        if not self._browser:
            raise RuntimeError("Browser not started")
        ctx = await self._browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=str(self.config.video_dir) if self.config.record_video else None,
        )
        ctx.set_default_timeout(self.config.timeout)
        page = await ctx.new_page()
        self._attach_listeners(page)
        return page

    async def get_video_path(self) -> Optional[str]:
        if self._page and self._page.video:
            try:
                return await self._page.video.path()
            except Exception:
                return None
        return None

    async def stop(self) -> Optional[str]:
        video_path = None
        if self._page and self._page.video:
            try:
                video_path = await self._page.video.path()
            except Exception:
                pass

        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        return video_path

    def get_page(self) -> Optional[Page]:
        return self._page

    async def goto(self, url: str) -> None:
        if not self._page:
            raise RuntimeError("Browser not started")
        try:
            await self._page.goto(url, wait_until="domcontentloaded")
        except Exception as e:
            logger.warning(f"Navigation to {url}: {e}")

    async def click(self, selector: str) -> None:
        if not self._page:
            raise RuntimeError("Browser not started")
        await self._page.click(selector)

    async def fill(self, selector: str, text: str) -> None:
        if not self._page:
            raise RuntimeError("Browser not started")
        await self._page.fill(selector, text)

    async def screenshot(self, path: str | Path) -> str:
        if not self._page:
            raise RuntimeError("Browser not started")
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        await self._page.screenshot(path=str(filepath))
        return str(filepath)

    async def current_url(self) -> str:
        if not self._page:
            raise RuntimeError("Browser not started")
        return self._page.url

    async def current_title(self) -> str:
        if not self._page:
            raise RuntimeError("Browser not started")
        return await self._page.title()
