import aiosqlite
from config import DB_NAME

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Опубликованные посты
        await db.execute('''
            CREATE TABLE IF NOT EXISTS published_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT UNIQUE,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Черновики на модерации
        await db.execute('''
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT UNIQUE,
                post_text TEXT,
                title TEXT,
                source_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        await db.commit()

async def is_published(url: str) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            'SELECT 1 FROM published_posts WHERE source_url = ?', 
            (url,)
        )
        return await cursor.fetchone() is not None

async def mark_published(url: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT OR IGNORE INTO published_posts (source_url) VALUES (?)',
            (url,)
        )
        await db.commit()

async def save_draft(url: str, text: str, title: str, source: str) -> int:
    """Сохраняем черновик, возвращаем ID"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR REPLACE INTO drafts (source_url, post_text, title, source_name, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (url, text, title, source))
        await db.commit()
        
        cursor = await db.execute('SELECT id FROM drafts WHERE source_url = ?', (url,))
        row = await cursor.fetchone()
        return row[0] if row else 1

async def get_draft(draft_id: int) -> dict:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM drafts WHERE id = ?', (draft_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_draft_text(draft_id: int, text: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE drafts SET post_text = ? WHERE id = ?', (text, draft_id))
        await db.commit()

async def delete_draft(draft_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM drafts WHERE id = ?', (draft_id,))
        await db.commit()

async def publish_draft(draft_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE drafts SET status = 'published' WHERE id = ?", (draft_id,))
        await db.commit()