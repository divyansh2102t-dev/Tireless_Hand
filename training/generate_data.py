import asyncio
import json
import random
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@dataclass
class TrainingExample:
    instruction: str
    input: str
    output: str
    task_type: str

RESOLUTION_TEMPLATES = [
    "Find the {description} in this DOM",
    "Which element is the {description}?",
    "Locate the {description}",
    "What ref_id corresponds to the {description}?",
    "Find: {description}",
    "Target: {description}",
]

def describe_element(tag: str, text: str, role: Optional[str], placeholder: Optional[str], el_type: Optional[str]) -> list[str]:
    descriptions = []
    
    if text:
        clean_text = text.strip()[:50]
        if tag == "button" or role == "button":
            descriptions.extend([
                f'"{clean_text}" button',
                f"button that says {clean_text}",
                f"the {clean_text} button",
                f"submit button" if "submit" in clean_text.lower() else f"button labeled {clean_text}",
            ])
        elif tag == "a" or role == "link":
            descriptions.extend([
                f'"{clean_text}" link',
                f"link to {clean_text}",
                f"the {clean_text} link",
            ])
        elif tag in ("input", "textarea") or role in ("textbox", "searchbox"):
            field_type = el_type or "text"
            descriptions.extend([
                f"{clean_text} input field",
                f"the {clean_text} field",
                f"{field_type} input for {clean_text}",
            ])
        else:
            descriptions.append(f'element with text "{clean_text}"')
    
    if placeholder:
        descriptions.extend([
            f"field with placeholder '{placeholder}'",
            f"input that says '{placeholder}'",
        ])
    
    if role and text:
        descriptions.append(f"{role} '{text.strip()[:30]}'")
    
    return descriptions if descriptions else [f"{tag} element"]

async def extract_compact_dom(page) -> tuple[str, list[dict]]:
    elements = []
    ref_id = 0
    
    interactable_selectors = [
        "a[href]", "button", "input", "textarea", "select",
        "[role='button']", "[role='link']", "[role='textbox']",
        "[role='checkbox']", "[role='radio']", "[role='tab']",
        "[onclick]", "[tabindex]",
    ]
    
    for selector in interactable_selectors:
        try:
            locators = page.locator(selector)
            count = await locators.count()
            for i in range(min(count, 50)):
                try:
                    el = locators.nth(i)
                    if not await el.is_visible():
                        continue
                    
                    ref_id += 1
                    tag = await el.evaluate("el => el.tagName.toLowerCase()")
                    text = (await el.inner_text()).strip()[:80] if tag not in ("input", "textarea") else ""
                    role = await el.get_attribute("role") or ""
                    aria_label = await el.get_attribute("aria-label") or ""
                    el_id = await el.get_attribute("id") or ""
                    name = await el.get_attribute("name") or ""
                    el_type = await el.get_attribute("type") or ""
                    placeholder = await el.get_attribute("placeholder") or ""
                    href = await el.get_attribute("href") or ""
                    
                    element = {
                        "ref_id": ref_id,
                        "tag": tag,
                        "text": text,
                        "role": role,
                        "aria_label": aria_label,
                        "id": el_id,
                        "name": name,
                        "type": el_type,
                        "placeholder": placeholder,
                        "href": href[:60] if href else "",
                    }
                    elements.append(element)
                except Exception:
                    continue
        except Exception:
            continue
    
    lines = []
    title = await page.title()
    url = page.url
    lines.append(f'Page: "{title}" ({url})')
    lines.append("---")
    
    seen_ids = set()
    for el in elements:
        if el["ref_id"] in seen_ids:
            continue
        seen_ids.add(el["ref_id"])
        
        parts = [f"[{el['ref_id']}]", el["tag"]]
        if el["text"]:
            parts.append(f'"{el["text"]}"')
        if el["role"]:
            parts.append(f"role={el['role']}")
        if el["aria_label"]:
            parts.append(f'aria-label="{el["aria_label"]}"')
        if el["placeholder"]:
            parts.append(f'placeholder="{el["placeholder"]}"')
        if el["type"]:
            parts.append(f"type={el['type']}")
        if el["href"]:
            parts.append(f'href="{el["href"]}"')
        
        lines.append(" ".join(parts))
    
    return "\n".join(lines), elements

def generate_resolution_examples(compact_dom: str, elements: list[dict]) -> list[TrainingExample]:
    examples = []
    
    for el in elements:
        descriptions = describe_element(
            el["tag"], el["text"], el["role"] or None,
            el["placeholder"] or None, el["type"] or None,
        )
        
        for desc in descriptions[:2]:
            template = random.choice(RESOLUTION_TEMPLATES)
            instruction = template.format(description=desc)
            
            examples.append(TrainingExample(
                instruction=instruction,
                input=compact_dom,
                output=str(el["ref_id"]),
                task_type="element_resolution",
            ))
    
    return examples

def generate_change_examples(dom_before: str, dom_after: str, change_type: str) -> list[TrainingExample]:
    instruction = (
        "Compare the baseline DOM with the current DOM. "
        "Classify the change as: BUG, FEATURE, COSMETIC, or MOVED. "
        "Respond with JSON: {\"verdict\": \"...\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\"}"
    )
    
    input_text = f"BASELINE:\n{dom_before}\n\nCURRENT:\n{dom_after}"
    
    verdicts = {
        "bug": '{"verdict": "BUG", "confidence": 0.9, "reasoning": "Error state detected, expected content missing"}',
        "feature": '{"verdict": "FEATURE", "confidence": 0.85, "reasoning": "New elements added, existing functionality preserved"}',
        "cosmetic": '{"verdict": "COSMETIC", "confidence": 0.9, "reasoning": "Only text/styling changes, no functional difference"}',
        "moved": '{"verdict": "MOVED", "confidence": 0.85, "reasoning": "Same element found at different position"}',
    }
    
    return [TrainingExample(
        instruction=instruction,
        input=input_text,
        output=verdicts.get(change_type, verdicts["cosmetic"]),
        task_type="change_classification",
    )]

def mutate_dom(compact_dom: str, elements: list[dict]) -> tuple[str, str, str]:
    lines = compact_dom.split("\n")
    mutation_type = random.choice(["remove_element", "change_text", "move_element", "add_error"])
    
    if mutation_type == "remove_element" and len(lines) > 3:
        idx = random.randint(2, len(lines) - 1)
        mutated = lines[:idx] + lines[idx+1:]
        return "\n".join(mutated), "bug", "Element removed"
    
    elif mutation_type == "change_text" and elements:
        el = random.choice(elements)
        old_text = el.get("text", "")
        if old_text:
            new_text = old_text + " (Updated)"
            mutated_dom = compact_dom.replace(f'"{old_text}"', f'"{new_text}"')
            return mutated_dom, "cosmetic", f"Text changed from '{old_text}' to '{new_text}'"
    
    elif mutation_type == "move_element" and len(lines) > 4:
        idx = random.randint(2, len(lines) - 1)
        new_idx = random.randint(2, len(lines) - 1)
        line = lines.pop(idx)
        lines.insert(new_idx, line)
        return "\n".join(lines), "moved", "Element repositioned"
    
    elif mutation_type == "add_error":
        error_line = f'[{len(elements)+1}] div "Error: Something went wrong" role=alert'
        lines.append(error_line)
        if lines[0].startswith('Page:'):
            lines[0] = lines[0].replace('Page:', 'Page: "Error -')
        return "\n".join(lines), "bug", "Error state appeared"
    
    return compact_dom, "cosmetic", "No change"

async def crawl_and_generate(url: str, max_pages: int = 5) -> list[TrainingExample]:
    all_examples = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        visited = set()
        to_visit = [url]
        
        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue
            
            try:
                await page.goto(current_url, timeout=15000)
                await page.wait_for_load_state("domcontentloaded")
                visited.add(current_url)
                
                compact_dom, elements = await extract_compact_dom(page)
                
                if elements:
                    resolution_examples = generate_resolution_examples(compact_dom, elements)
                    all_examples.extend(resolution_examples)
                    
                    for _ in range(3):
                        mutated_dom, change_type, _ = mutate_dom(compact_dom, elements)
                        change_examples = generate_change_examples(compact_dom, mutated_dom, change_type)
                        all_examples.extend(change_examples)
                
                links = await page.locator("a[href]").all()
                for link in links[:20]:
                    try:
                        href = await link.get_attribute("href")
                        if href and not href.startswith(("#", "javascript:", "mailto:")):
                            if href.startswith("/"):
                                from urllib.parse import urljoin
                                href = urljoin(current_url, href)
                            if href.startswith(url.split("/")[0] + "//" + url.split("//")[1].split("/")[0]):
                                to_visit.append(href)
                    except Exception:
                        continue
                        
            except Exception:
                continue
        
        await browser.close()
    
    return all_examples

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str)
    parser.add_argument("--urls", type=str)
    parser.add_argument("--output", type=str, default="training/data/training.jsonl")
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--samples", type=int, default=0)
    args = parser.parse_args()
    
    urls = []
    if args.url:
        urls.append(args.url)
    elif args.urls:
        with open(args.urls) as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        urls = ["https://example.com", "https://www.wikipedia.org", "https://news.ycombinator.com"]
    
    all_examples = []
    for url in urls:
        examples = await crawl_and_generate(url, max_pages=args.max_pages)
        all_examples.extend(examples)
    
    random.shuffle(all_examples)
    if args.samples > 0:
        all_examples = all_examples[:args.samples]
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for example in all_examples:
            f.write(json.dumps(asdict(example), ensure_ascii=False) + "\n")

if __name__ == "__main__":
    asyncio.run(main())
