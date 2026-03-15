import aiosqlite
from datetime import datetime, timedelta
from config import DB_NAME, DEFAULT_SOURCES

async def init_db():
    """Инициализация базы данных и автоматическая миграция"""
    async with aiosqlite.connect(DB_NAME) as db:
        # 1. Создание таблиц (если их нет)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_end TIMESTAMP,
                target_channel_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                rss_url TEXT NOT NULL,
                keywords TEXT,
                enabled INTEGER DEFAULT 1,
                lang TEXT DEFAULT 'ru',
                priority TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                source_url TEXT,
                post_text TEXT,
                title TEXT,
                source_name TEXT,
                style TEXT,
                status TEXT DEFAULT 'pending',
                scheduled_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS published_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                source_url TEXT UNIQUE,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS rss_cache (
                url TEXT PRIMARY KEY,
                etag TEXT,
                last_modified TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                draft_id INTEGER,
                scheduled_time TIMESTAMP,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id),
                FOREIGN KEY (draft_id) REFERENCES drafts(id)
            )
        ''')
        
        # 2. МИГРАЦИЯ: Добавляем колонки в существующие таблицы (на случай старой БД)
        tables_to_fix = {
            "users": {
                "subscription_status": "TEXT DEFAULT 'inactive'",
                "subscription_end": "TIMESTAMP",
                "target_channel_id": "TEXT"
            },
            "drafts": {
                "user_id": "INTEGER",
                "style": "TEXT",
                "status": "TEXT DEFAULT 'pending'",
                "scheduled_at": "TIMESTAMP"
            }
        }
        
        for table, columns in tables_to_fix.items():
            for col_name, col_type in columns.items():
                try:
                    await db.execute(f'ALTER TABLE {table} ADD COLUMN {col_name} {col_type}')
                    print(f"➕ Колонка {col_name} добавлена в {table}")
                except:
                    pass # Колонка уже существует
        
        await db.commit()

# ===========================
# 👤 User Functions
# ===========================

async def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None):
    """Получить или создать пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (telegram_id, username, first_name)
            VALUES (?, ?, ?)
        ''', (telegram_id, username, first_name))
        await db.commit()
        
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def check_subscription(telegram_id: int) -> dict:
    """Проверить статус подписки"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            'SELECT subscription_status, subscription_end FROM users WHERE telegram_id = ?',
            (telegram_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return {'active': False, 'status': 'not_found'}
        
        if row['subscription_end']:
            end_time = datetime.fromisoformat(row['subscription_end'])
            if end_time < datetime.now():
                await db.execute(
                    'UPDATE users SET subscription_status = ? WHERE telegram_id = ?',
                    ('inactive', telegram_id)
                )
                await db.commit()
                return {'active': False, 'status': 'expired'}
        
        return {
            'active': row['subscription_status'] != 'inactive',
            'status': row['subscription_status'],
            'end': row['subscription_end']
        }

async def activate_subscription(telegram_id: int, tariff: str, days: int = 30):
    """Активировать подписку"""
    end_date = datetime.now() + timedelta(days=days)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            UPDATE users 
            SET subscription_status = ?, subscription_end = ?
            WHERE telegram_id = ?
        ''', (tariff, end_date.isoformat(), telegram_id))
        await db.commit()

async def set_user_channel(user_id: int, channel_id: str):
    """Привязать Telegram-канал"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'UPDATE users SET target_channel_id = ? WHERE telegram_id = ?',
            (channel_id, user_id)
        )
        await db.commit()

async def get_user_channel(user_id: int) -> str:
    """Получить ID привязанного канала"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            'SELECT target_channel_id FROM users WHERE telegram_id = ?',
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

# ===========================
# 📰 Source Functions
# ===========================

async def get_user_sources(user_id: int) -> list:
    """Получить все источники пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            'SELECT * FROM user_sources WHERE user_id = ? ORDER BY priority DESC, name',
            (user_id,)
        )
        return [dict(row) for row in await cursor.fetchall()]

async def add_user_source(user_id: int, name: str, rss_url: str, keywords: str, lang: str = 'ru', priority: str = 'medium'):
    """Добавить новый источник"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO user_sources (user_id, name, rss_url, keywords, lang, priority)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, name, rss_url, keywords, lang, priority))
        await db.commit()

async def toggle_source(user_id: int, source_id: int, enabled: bool):
    """Включить/выключить источник"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            UPDATE user_sources SET enabled = ? WHERE id = ? AND user_id = ?
        ''', (1 if enabled else 0, source_id, user_id))
        await db.commit()

async def delete_source(user_id: int, source_id: int):
    """Удалить источник"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            DELETE FROM user_sources WHERE id = ? AND user_id = ?
        ''', (source_id, user_id))
        await db.commit()

async def get_active_sources(user_id: int) -> list:
    """Получить активные источники"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            'SELECT * FROM user_sources WHERE user_id = ? AND enabled = 1',
            (user_id,)
        )
        return [dict(row) for row in await cursor.fetchall()]

async def initialize_default_sources(user_id: int):
    """Добавить источники по умолчанию"""
    for source in DEFAULT_SOURCES:
        await add_user_source(
            user_id=user_id,
            name=source['name'],
            rss_url=source['rss'],
            keywords=source['keywords'],
            lang=source['lang'],
            priority=source['priority']
        )

# ===========================
# 📝 Draft Functions
# ===========================

async def save_draft(user_id: int, source_url: str, text: str, title: str, source_name: str, style: str = None) -> int:
    """Сохранить черновик"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO drafts (user_id, source_url, post_text, title, source_name, style)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, source_url, text, title, source_name, style))
        await db.commit()
        
        cursor = await db.execute('SELECT last_insert_rowid()')
        row = await cursor.fetchone()
        return row[0]

async def get_draft(draft_id: int) -> dict:
    """Получить черновик по ID"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM drafts WHERE id = ?', (draft_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_user_drafts(user_id: int, status: str = 'pending', limit: int = 10) -> list:
    """Получить черновики пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            '''SELECT * FROM drafts 
               WHERE user_id = ? AND status = ? 
               ORDER BY created_at DESC 
               LIMIT ?''',
            (user_id, status, limit)
        )
        return [dict(row) for row in await cursor.fetchall()]

async def update_draft_text(draft_id: int, text: str):
    """Обновить текст черновика"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE drafts SET post_text = ? WHERE id = ?', (text, draft_id))
        await db.commit()

async def update_draft_status(draft_id: int, status: str):
    """Обновить статус черновика"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE drafts SET status = ? WHERE id = ?', (status, draft_id))
        await db.commit()

async def delete_draft(draft_id: int):
    """Удалить черновик"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM drafts WHERE id = ?', (draft_id,))
        await db.commit()

async def is_published(user_id: int, url: str) -> bool:
    """Проверить, опубликован ли уже пост"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            'SELECT 1 FROM published_posts WHERE user_id = ? AND source_url = ?',
            (user_id, url)
        )
        return await cursor.fetchone() is not None

async def mark_published(user_id: int, url: str):
    """Отметить пост как опубликованный"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR IGNORE INTO published_posts (user_id, source_url)
            VALUES (?, ?)
        ''', (user_id, url))
        await db.commit()

async def get_user_stats(user_id: int) -> dict:
    """Получить статистику пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT COUNT(*) as count FROM drafts WHERE user_id = ?", (user_id,))
        total = (await cursor.fetchone())['count']
        cursor = await db.execute("SELECT status, COUNT(*) as count FROM drafts WHERE user_id = ? GROUP BY status", (user_id,))
        status_counts = {row['status']: row['count'] for row in await cursor.fetchall()}
        cursor = await db.execute("SELECT COUNT(*) as count FROM user_sources WHERE user_id = ? AND enabled = 1", (user_id,))
        sources = (await cursor.fetchone())['count']
        return {
            'total_drafts': total,
            'pending': status_counts.get('pending', 0),
            'published': status_counts.get('published', 0),
            'skipped': status_counts.get('skipped', 0),
            'active_sources': sources
        }

# ===========================
# ⏰ Scheduling Functions
# ===========================

async def schedule_post(user_id: int, draft_id: int, scheduled_time: datetime):
    """Запланировать пост"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO scheduled_posts (user_id, draft_id, scheduled_time)
            VALUES (?, ?, ?)
        ''', (user_id, draft_id, scheduled_time.isoformat()))
        await db.execute('UPDATE drafts SET status = "scheduled" WHERE id = ?', (draft_id,))
        await db.commit()

async def get_due_scheduled_posts() -> list:
    """Получить посты, время публикации которых пришло"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT sp.id as sched_id, sp.user_id, sp.draft_id, d.post_text, u.target_channel_id
            FROM scheduled_posts sp
            JOIN drafts d ON sp.draft_id = d.id
            JOIN users u ON sp.user_id = u.telegram_id
            WHERE sp.status = 'pending' 
            AND sp.scheduled_time <= ?
        ''', (datetime.now().isoformat(),))
        return [dict(row) for row in await cursor.fetchall()]

async def mark_scheduled_published(scheduled_id: int):
    """Отметить запланированный пост как опубликованный"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE scheduled_posts SET status = "published" WHERE id = ?', (scheduled_id,))
        cursor = await db.execute('SELECT draft_id FROM scheduled_posts WHERE id = ?', (scheduled_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute('UPDATE drafts SET status = "published" WHERE id = ?', (row[0],))
        await db.commit()
