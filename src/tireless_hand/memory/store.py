import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path

import aiosqlite

@dataclass
class PageRecord:
    id: str
    url: str
    title: str
    dom_hash: str
    last_visited: datetime
    visit_count: int

@dataclass
class ElementRecord:
    id: str
    page_id: str
    tag: str
    role: str
    text_content: str
    selector: str
    fingerprint_json: str
    last_seen: datetime

@dataclass
class TransitionRecord:
    id: str
    from_page_id: str
    to_page_id: str
    trigger_element_id: str
    action: str

@dataclass
class FlowRecord:
    id: str
    name: str
    description: str
    steps_json: str
    status: str
    created: datetime
    last_run: datetime
    run_count: int

@dataclass
class BaselineRecord:
    id: str
    page_id: str
    dom_snapshot: str
    screenshot_hash: str
    created: datetime

@dataclass
class HealingRecord:
    id: str
    element_id: str
    old_selector: str
    new_selector: str
    strategy: str
    similarity: float
    timestamp: datetime


class MemoryStore:
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS pages (
                    id TEXT PRIMARY KEY,
                    url TEXT,
                    title TEXT,
                    dom_hash TEXT,
                    last_visited DATETIME,
                    visit_count INT
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS elements (
                    id TEXT PRIMARY KEY,
                    page_id TEXT,
                    tag TEXT,
                    role TEXT,
                    text_content TEXT,
                    selector TEXT,
                    fingerprint_json TEXT,
                    last_seen DATETIME,
                    FOREIGN KEY(page_id) REFERENCES pages(id)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS transitions (
                    id TEXT PRIMARY KEY,
                    from_page_id TEXT,
                    to_page_id TEXT,
                    trigger_element_id TEXT,
                    action TEXT,
                    FOREIGN KEY(from_page_id) REFERENCES pages(id),
                    FOREIGN KEY(to_page_id) REFERENCES pages(id),
                    FOREIGN KEY(trigger_element_id) REFERENCES elements(id)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS flows (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    steps_json TEXT,
                    status TEXT,
                    created DATETIME,
                    last_run DATETIME,
                    run_count INT
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS baselines (
                    id TEXT PRIMARY KEY,
                    page_id TEXT,
                    dom_snapshot TEXT,
                    screenshot_hash TEXT,
                    created DATETIME,
                    FOREIGN KEY(page_id) REFERENCES pages(id)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS healing_log (
                    id TEXT PRIMARY KEY,
                    element_id TEXT,
                    old_selector TEXT,
                    new_selector TEXT,
                    strategy TEXT,
                    similarity REAL,
                    timestamp DATETIME,
                    FOREIGN KEY(element_id) REFERENCES elements(id)
                )
            ''')
            await db.commit()

    async def save_page(self, page_info: PageRecord) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO pages (id, url, title, dom_hash, last_visited, visit_count)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    url=excluded.url,
                    title=excluded.title,
                    dom_hash=excluded.dom_hash,
                    last_visited=excluded.last_visited,
                    visit_count=excluded.visit_count
            ''', (page_info.id, page_info.url, page_info.title, page_info.dom_hash, 
                  page_info.last_visited.isoformat(), page_info.visit_count))
            await db.commit()

    async def get_page(self, url: str) -> Optional[PageRecord]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM pages WHERE url = ?', (url,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return PageRecord(
                        id=row['id'],
                        url=row['url'],
                        title=row['title'],
                        dom_hash=row['dom_hash'],
                        last_visited=datetime.fromisoformat(row['last_visited']),
                        visit_count=row['visit_count']
                    )
        return None

    async def save_element(self, element_info: ElementRecord) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO elements (id, page_id, tag, role, text_content, selector, fingerprint_json, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    page_id=excluded.page_id,
                    tag=excluded.tag,
                    role=excluded.role,
                    text_content=excluded.text_content,
                    selector=excluded.selector,
                    fingerprint_json=excluded.fingerprint_json,
                    last_seen=excluded.last_seen
            ''', (element_info.id, element_info.page_id, element_info.tag, element_info.role, 
                  element_info.text_content, element_info.selector, element_info.fingerprint_json, 
                  element_info.last_seen.isoformat()))
            await db.commit()

    async def get_elements_for_page(self, page_id: str) -> List[ElementRecord]:
        elements = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM elements WHERE page_id = ?', (page_id,)) as cursor:
                async for row in cursor:
                    elements.append(ElementRecord(
                        id=row['id'],
                        page_id=row['page_id'],
                        tag=row['tag'],
                        role=row['role'],
                        text_content=row['text_content'],
                        selector=row['selector'],
                        fingerprint_json=row['fingerprint_json'],
                        last_seen=datetime.fromisoformat(row['last_seen'])
                    ))
        return elements

    async def save_transition(self, from_page: PageRecord, to_page: PageRecord, trigger: ElementRecord) -> None:
        action = "click"
        transition_id = str(uuid.uuid4())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO transitions (id, from_page_id, to_page_id, trigger_element_id, action)
                VALUES (?, ?, ?, ?, ?)
            ''', (transition_id, from_page.id, to_page.id, trigger.id, action))
            await db.commit()

    async def save_flow(self, flow: FlowRecord) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO flows (id, name, description, steps_json, status, created, last_run, run_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    steps_json=excluded.steps_json,
                    status=excluded.status,
                    last_run=excluded.last_run,
                    run_count=excluded.run_count
            ''', (flow.id, flow.name, flow.description, flow.steps_json, flow.status, 
                  flow.created.isoformat(), flow.last_run.isoformat(), flow.run_count))
            await db.commit()

    async def get_flow(self, name: str) -> Optional[FlowRecord]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM flows WHERE name = ?', (name,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return FlowRecord(
                        id=row['id'],
                        name=row['name'],
                        description=row['description'],
                        steps_json=row['steps_json'],
                        status=row['status'],
                        created=datetime.fromisoformat(row['created']),
                        last_run=datetime.fromisoformat(row['last_run']),
                        run_count=row['run_count']
                    )
        return None

    async def get_all_flows(self) -> List[FlowRecord]:
        flows = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM flows') as cursor:
                async for row in cursor:
                    flows.append(FlowRecord(
                        id=row['id'],
                        name=row['name'],
                        description=row['description'],
                        steps_json=row['steps_json'],
                        status=row['status'],
                        created=datetime.fromisoformat(row['created']),
                        last_run=datetime.fromisoformat(row['last_run']),
                        run_count=row['run_count']
                    ))
        return flows

    async def save_baseline(self, page_id: str, dom_snapshot: str, screenshot_hash: str) -> None:
        baseline_id = str(uuid.uuid4())
        created = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO baselines (id, page_id, dom_snapshot, screenshot_hash, created)
                VALUES (?, ?, ?, ?, ?)
            ''', (baseline_id, page_id, dom_snapshot, screenshot_hash, created))
            await db.commit()

    async def get_baseline(self, page_id: str) -> Optional[BaselineRecord]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM baselines WHERE page_id = ? ORDER BY created DESC LIMIT 1', (page_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return BaselineRecord(
                        id=row['id'],
                        page_id=row['page_id'],
                        dom_snapshot=row['dom_snapshot'],
                        screenshot_hash=row['screenshot_hash'],
                        created=datetime.fromisoformat(row['created'])
                    )
        return None

    async def log_healing(self, element_id: str, old_sel: str, new_sel: str, strategy: str, similarity: float) -> None:
        healing_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO healing_log (id, element_id, old_selector, new_selector, strategy, similarity, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (healing_id, element_id, old_sel, new_sel, strategy, similarity, now))
            await db.commit()

    async def get_healing_stats(self) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT count(*) as total, avg(similarity) as avg_sim FROM healing_log') as cursor:
                row = await cursor.fetchone()
                return {
                    "total_healings": row['total'] if row and row['total'] else 0,
                    "average_similarity": row['avg_sim'] if row and row['avg_sim'] else 0.0
                }

    async def get_known_pages(self) -> List[PageRecord]:
        pages = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM pages') as cursor:
                async for row in cursor:
                    pages.append(PageRecord(
                        id=row['id'],
                        url=row['url'],
                        title=row['title'],
                        dom_hash=row['dom_hash'],
                        last_visited=datetime.fromisoformat(row['last_visited']),
                        visit_count=row['visit_count']
                    ))
        return pages
