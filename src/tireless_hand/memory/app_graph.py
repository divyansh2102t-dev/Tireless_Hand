import uuid
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

from .store import MemoryStore, PageRecord, ElementRecord, TransitionRecord
import aiosqlite

@dataclass
class PageNode:
    url: str
    title: str
    element_count: int
    visit_count: int
    transitions_out: List[Tuple[str, str]] = field(default_factory=list)


class AppGraph:
    def __init__(self, store: MemoryStore):
        self.store = store

    async def record_page(self, url: str, title: str, elements: List[Dict[str, Any]], dom_hash: str) -> str:
        page = await self.store.get_page(url)
        now = datetime.now(timezone.utc)
        
        if page:
            page.title = title
            page.dom_hash = dom_hash
            page.last_visited = now
            page.visit_count += 1
            await self.store.save_page(page)
            page_id = page.id
        else:
            page_id = str(uuid.uuid4())
            page = PageRecord(
                id=page_id,
                url=url,
                title=title,
                dom_hash=dom_hash,
                last_visited=now,
                visit_count=1
            )
            await self.store.save_page(page)
            
        for el_data in elements:
            el_id = str(uuid.uuid4())
            element = ElementRecord(
                id=el_id,
                page_id=page_id,
                tag=el_data.get('tag', ''),
                role=el_data.get('role', ''),
                text_content=el_data.get('text_content', ''),
                selector=el_data.get('selector', ''),
                fingerprint_json=json.dumps(el_data.get('fingerprint', {})),
                last_seen=now
            )
            await self.store.save_element(element)
            
        return page_id

    async def record_transition(self, from_url: str, to_url: str, action: str, element: Dict[str, Any]) -> None:
        from_page = await self.store.get_page(from_url)
        to_page = await self.store.get_page(to_url)
        
        if not from_page or not to_page:
            return
            
        trigger_element_id = ""
        elements = await self.store.get_elements_for_page(from_page.id)
        fp_str = json.dumps(element)
        for el in elements:
            if el.fingerprint_json == fp_str:
                trigger_element_id = el.id
                break
                
        if not trigger_element_id:
            trigger_element_id = str(uuid.uuid4())
                
        transition = TransitionRecord(
            id=str(uuid.uuid4()),
            from_page_id=from_page.id,
            to_page_id=to_page.id,
            trigger_element_id=trigger_element_id,
            action=action
        )
        async with aiosqlite.connect(self.store.db_path) as db:
            await db.execute('''
                INSERT INTO transitions (id, from_page_id, to_page_id, trigger_element_id, action)
                VALUES (?, ?, ?, ?, ?)
            ''', (transition.id, transition.from_page_id, transition.to_page_id, transition.trigger_element_id, transition.action))
            await db.commit()

    async def get_page_map(self) -> Dict[str, PageNode]:
        pages = await self.store.get_known_pages()
        page_map = {}
        for p in pages:
            elements = await self.store.get_elements_for_page(p.id)
            transitions = await self.get_transitions_from(p.url)
            node = PageNode(
                url=p.url,
                title=p.title,
                element_count=len(elements),
                visit_count=p.visit_count,
                transitions_out=transitions
            )
            page_map[p.url] = node
        return page_map

    async def get_transitions_from(self, url: str) -> List[Tuple[str, str]]:
        page = await self.store.get_page(url)
        if not page:
            return []
        
        transitions_out = []
        async with aiosqlite.connect(self.store.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT t.action, p.url 
                FROM transitions t 
                JOIN pages p ON t.to_page_id = p.id 
                WHERE t.from_page_id = ?
            ''', (page.id,)) as cursor:
                async for row in cursor:
                    transitions_out.append((row['action'], row['url']))
        return transitions_out

    async def is_known_page(self, url: str) -> bool:
        page = await self.store.get_page(url)
        return page is not None

    async def get_known_elements(self, url: str) -> List[Dict[str, Any]]:
        page = await self.store.get_page(url)
        if not page:
            return []
        elements = await self.store.get_elements_for_page(page.id)
        return [json.loads(el.fingerprint_json) for el in elements]

    async def find_element_in_memory(self, fingerprint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fp_str = json.dumps(fingerprint)
        async with aiosqlite.connect(self.store.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT fingerprint_json FROM elements WHERE fingerprint_json = ? LIMIT 1', (fp_str,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row['fingerprint_json'])
        return None

    async def get_exploration_coverage(self) -> Dict[str, Any]:
        pages = await self.store.get_known_pages()
        total_elements = 0
        for p in pages:
            els = await self.store.get_elements_for_page(p.id)
            total_elements += len(els)
            
        return {
            "total_pages": len(pages),
            "total_elements": total_elements
        }
