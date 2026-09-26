from pathlib import Path
import imagehash
from PIL import Image, ImageChops
from playwright.async_api import Page
import time

class ScreenshotManager:
    def __init__(self, base_dir: Path = Path("./reports/screenshots")):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    async def capture(self, page: Page, name: str, full_page: bool = False) -> Path:
        timestamp = int(time.time())
        filename = f"{name}_{timestamp}.png"
        filepath = self.base_dir / filename
        await page.screenshot(path=str(filepath), full_page=full_page)
        return filepath
        
    def compare(self, img1_path: str | Path, img2_path: str | Path) -> float:
        img1 = Image.open(img1_path)
        img2 = Image.open(img2_path)
        
        hash1 = imagehash.phash(img1)
        hash2 = imagehash.phash(img2)
        
        diff = hash1 - hash2
        similarity = 1.0 - (diff / 64.0)
        return max(0.0, similarity)
        
    def diff(self, img1_path: str | Path, img2_path: str | Path) -> Image.Image:
        img1 = Image.open(img1_path).convert("RGB")
        img2 = Image.open(img2_path).convert("RGB")
        
        if img1.size != img2.size:
            img2 = img2.resize(img1.size)
            
        return ImageChops.difference(img1, img2)
