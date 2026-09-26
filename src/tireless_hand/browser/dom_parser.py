import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


@dataclass
class ElementInfo:
    ref_id: int
    role: str
    name: str
    tag: str = ""
    text: str = ""
    aria_label: str = ""
    id_attr: str = ""
    name_attr: str = ""
    type_attr: str = ""
    placeholder: str = ""
    href: str = ""
    bounding_box: Dict[str, float] = field(default_factory=dict)
    visible: bool = True
    enabled: bool = True
    checked: Optional[bool] = None


class DOMParser:
    def __init__(self):
        self._element_map: Dict[int, ElementInfo] = {}

    async def get_compact_dom(self, page: Page) -> str:
        url = page.url
        title = await page.title()
        elements = await self.get_interactable_elements(page)

        lines = [f'Page: "{title}" ({url})', "---"]
        for el in elements:
            parts = [f"[{el.ref_id}]", el.role]
            if el.name:
                parts.append(f'"{el.name}"')
            if el.type_attr:
                parts.append(f"type={el.type_attr}")
            if el.placeholder:
                parts.append(f'placeholder="{el.placeholder}"')
            if el.href:
                parts.append(f'href="{el.href}"')
            if not el.enabled:
                parts.append("disabled=true")
            if el.checked is not None:
                parts.append(f"checked={str(el.checked).lower()}")

            lines.append(" ".join(parts))

        return "\n".join(lines)

    async def get_element_details(self, page: Page, ref_id: int) -> Optional[dict]:
        element = self._element_map.get(ref_id)
        if element:
            from dataclasses import asdict

            return asdict(element)
        return None

    async def get_interactable_elements(self, page: Page) -> List[ElementInfo]:
        js_script = """
        () => {
            const elements = [];
            
            function isVisible(el) {
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetWidth > 0 && el.offsetHeight > 0;
            }
            
            const iter = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_ELEMENT);
            let node;
            while (node = iter.nextNode()) {
                if (!isVisible(node)) continue;
                
                const tag = node.tagName.toLowerCase();
                if (['script', 'style', 'svg', 'noscript', 'meta', 'link'].includes(tag)) continue;
                
                const isClickable = node.onclick != null || node.hasAttribute('onclick') || node.getAttribute('role') === 'button';
                const isInput = ['input', 'textarea', 'select', 'button'].includes(tag);
                const isLink = tag === 'a' && node.hasAttribute('href');
                const isImportantText = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tag);
                const role = node.getAttribute('role');
                const interactableRoles = ['button', 'link', 'checkbox', 'menuitem', 'tab', 'textbox', 'heading'];
                
                if (isInput || isLink || isClickable || isImportantText || (role && interactableRoles.includes(role))) {
                    const rect = node.getBoundingClientRect();
                    elements.push({
                        tag: tag,
                        role: role || (isLink ? 'link' : (isImportantText ? 'heading' : (tag === 'button' ? 'button' : tag))),
                        text: (node.innerText || node.textContent || '').trim(),
                        aria_label: node.getAttribute('aria-label') || '',
                        id: node.id || '',
                        name: node.getAttribute('name') || '',
                        type: node.getAttribute('type') || '',
                        placeholder: node.getAttribute('placeholder') || '',
                        href: node.getAttribute('href') || '',
                        disabled: node.disabled || node.getAttribute('aria-disabled') === 'true',
                        checked: node.checked,
                        bounding_box: {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
                    });
                }
            }
            return elements;
        }
        """
        try:
            dom_elements = await page.evaluate(js_script)
            self._element_map.clear()
            rich_elements: List[ElementInfo] = []

            for idx, item in enumerate(dom_elements, start=1):
                text = item["text"].replace("\n", " ")
                if len(text) > 80:
                    text = text[:77] + "..."

                name = item["aria_label"] or text or item["placeholder"] or item["name"] or item["tag"]
                el = ElementInfo(
                    ref_id=idx,
                    role=item["role"],
                    name=name,
                    tag=item["tag"],
                    text=text,
                    aria_label=item["aria_label"],
                    id_attr=item["id"],
                    name_attr=item["name"],
                    type_attr=item["type"],
                    placeholder=item["placeholder"],
                    href=item["href"],
                    bounding_box=item["bounding_box"],
                    enabled=not item["disabled"],
                    checked=item["checked"],
                )
                rich_elements.append(el)
                self._element_map[idx] = el

            return rich_elements

        except Exception as e:
            logger.error(f"Error evaluating JS for DOM extraction: {e}")
            return []
