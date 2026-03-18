import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update, delete, func
from config import DATABASE_URL, DEFAULT_SOURCES
from models import User, Channel, Source, Draft, PublishedPost, ScheduledPost, RssCache

# Создаем движок
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    # Поскольку мы используем Alembic, нам больше не нужно делать create_all() здесь.
    # Но для отладки или первоначального запуска можно оставить:
    pass

# ===========================
# 👤 User Functions
# ===========================

async def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalars().first()
        
        if not user:
            user = User(telegram_id=telegram_id, username=username, first_name=first_name)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user

async def get_user(telegram_id: int) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalars().first()

async def check_subscription(telegram_id: int) -> dict:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalars().first()
        
        if not user:
            return {'active': False, 'status': 'not_found'}
            
        if user.subscription_end and user.subscription_end < datetime.now():
            user.subscription_status = 'inactive'
            await session.commit()
            return {'active': False, 'status': 'expired'}
            
        return {
            'active': user.subscription_status != 'inactive',
            'status': user.subscription_status,
            'end': user.subscription_end
        }

async def activate_subscription(telegram_id: int, tariff: str, days: int = 30):
    end_date = datetime.now() + timedelta(days=days)
    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(subscription_status=tariff, subscription_end=end_date)
        )
        await session.commit()

async def set_active_channel(user_id: int, channel_id: int):
    async with async_session() as session:
        await session.execute(
            update(User).where(User.telegram_id == user_id).values(active_channel_id=channel_id)
        )
        await session.commit()

# ===========================
# 📢 Channel Functions
# ===========================

async def get_user_channels(user_id: int) -> list[Channel]:
    async with async_session() as session:
        result = await session.execute(select(Channel).where(Channel.user_id == user_id))
        return list(result.scalars().all())

async def get_channel(channel_id: int) -> Channel:
    async with async_session() as session:
        result = await session.execute(select(Channel).where(Channel.id == channel_id))
        return result.scalars().first()

async def add_channel(user_id: int, tg_channel_id: str, name: str) -> Channel:
    async with async_session() as session:
        channel = Channel(user_id=user_id, tg_channel_id=tg_channel_id, name=name)
        session.add(channel)
        await session.commit()
        await session.refresh(channel)
        return channel

async def delete_channel(channel_id: int):
    async with async_session() as session:
        await session.execute(delete(Channel).where(Channel.id == channel_id))
        await session.commit()

# ===========================
# 📰 Source Functions
# ===========================

async def get_channel_sources(channel_id: int) -> list[Source]:
    async with async_session() as session:
        result = await session.execute(
            select(Source)
            .where(Source.channel_id == channel_id)
            .order_by(Source.priority.desc(), Source.name)
        )
        return list(result.scalars().all())

async def add_channel_source(channel_id: int, name: str, rss_url: str, keywords: str, lang: str = 'ru', priority: str = 'medium'):
    async with async_session() as session:
        source = Source(channel_id=channel_id, name=name, rss_url=rss_url, keywords=keywords, lang=lang, priority=priority)
        session.add(source)
        await session.commit()

async def toggle_source(source_id: int, enabled: bool):
    async with async_session() as session:
        await session.execute(
            update(Source).where(Source.id == source_id).values(enabled=enabled)
        )
        await session.commit()

async def delete_source(source_id: int):
    async with async_session() as session:
        await session.execute(delete(Source).where(Source.id == source_id))
        await session.commit()

async def get_active_sources(channel_id: int) -> list[Source]:
    async with async_session() as session:
        result = await session.execute(
            select(Source).where(Source.channel_id == channel_id, Source.enabled == True)
        )
        return list(result.scalars().all())

async def initialize_default_sources(channel_id: int):
    for source in DEFAULT_SOURCES:
        await add_channel_source(
            channel_id=channel_id,
            name=source['name'],
            rss_url=source['rss'],
            keywords=source['keywords'],
            lang=source['lang'],
            priority=source['priority']
        )

# ===========================
# 📝 Draft Functions
# ===========================

async def save_draft(channel_id: int, source_url: str, text: str, title: str, source_name: str, style: str = None, image_url: str = None) -> int:
    async with async_session() as session:
        draft = Draft(
            channel_id=channel_id, 
            source_url=source_url, 
            post_text=text, 
            title=title, 
            source_name=source_name, 
            style=style,
            image_url=image_url
        )
        session.add(draft)
        await session.commit()
        await session.refresh(draft)
        return draft.id

async def get_draft(draft_id: int) -> Draft:
    async with async_session() as session:
        result = await session.execute(select(Draft).where(Draft.id == draft_id))
        return result.scalars().first()

async def get_channel_drafts(channel_id: int, status: str = 'pending', limit: int = 10) -> list[Draft]:
    async with async_session() as session:
        result = await session.execute(
            select(Draft)
            .where(Draft.channel_id == channel_id, Draft.status == status)
            .order_by(Draft.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

async def update_draft_text(draft_id: int, text: str):
    async with async_session() as session:
        await session.execute(update(Draft).where(Draft.id == draft_id).values(post_text=text))
        await session.commit()

async def update_draft_status(draft_id: int, status: str):
    async with async_session() as session:
        await session.execute(update(Draft).where(Draft.id == draft_id).values(status=status))
        await session.commit()

async def delete_draft(draft_id: int):
    async with async_session() as session:
        await session.execute(delete(Draft).where(Draft.id == draft_id))
        await session.commit()

async def is_published(channel_id: int, url: str) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(PublishedPost).where(PublishedPost.channel_id == channel_id, PublishedPost.source_url == url)
        )
        return result.scalars().first() is not None

async def mark_published(channel_id: int, url: str):
    async with async_session() as session:
        if not await is_published(channel_id, url):
            post = PublishedPost(channel_id=channel_id, source_url=url)
            session.add(post)
            await session.commit()

async def get_channel_stats(channel_id: int) -> dict:
    async with async_session() as session:
        # Total drafts
        total_res = await session.execute(select(func.count(Draft.id)).where(Draft.channel_id == channel_id))
        total = total_res.scalar() or 0
        
        # Drafts by status
        status_res = await session.execute(
            select(Draft.status, func.count(Draft.id))
            .where(Draft.channel_id == channel_id)
            .group_by(Draft.status)
        )
        status_counts = dict(status_res.all())
        
        # Active sources
        sources_res = await session.execute(
            select(func.count(Source.id)).where(Source.channel_id == channel_id, Source.enabled == True)
        )
        sources = sources_res.scalar() or 0
        
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

async def schedule_post(channel_id: int, draft_id: int, scheduled_time: datetime):
    async with async_session() as session:
        sp = ScheduledPost(channel_id=channel_id, draft_id=draft_id, scheduled_time=scheduled_time)
        session.add(sp)
        await session.execute(update(Draft).where(Draft.id == draft_id).values(status="scheduled"))
        await session.commit()

async def get_due_scheduled_posts() -> list[dict]:
    # Returns a list of dicts to make handler logic easier
    async with async_session() as session:
        # Join ScheduledPost, Draft, Channel
        stmt = (
            select(ScheduledPost, Draft, Channel)
            .join(Draft, ScheduledPost.draft_id == Draft.id)
            .join(Channel, ScheduledPost.channel_id == Channel.id)
            .where(ScheduledPost.status == 'pending', ScheduledPost.scheduled_time <= datetime.now())
        )
        result = await session.execute(stmt)
        due_posts = []
        for sp, draft, channel in result.all():
            due_posts.append({
                'sched_id': sp.id,
                'draft_id': draft.id,
                'post_text': draft.post_text,
                'image_url': draft.image_url,
                'target_channel_id': channel.tg_channel_id
            })
        return due_posts

async def mark_scheduled_published(scheduled_id: int):
    async with async_session() as session:
        sp = await session.get(ScheduledPost, scheduled_id)
        if sp:
            sp.status = "published"
            await session.execute(update(Draft).where(Draft.id == sp.draft_id).values(status="published"))
            await session.commit()

# ===========================
# RSS Cache
# ===========================

async def get_rss_cache(url: str) -> tuple[str, str]:
    async with async_session() as session:
        cache = await session.get(RssCache, url)
        if cache:
            return cache.etag, cache.last_modified
        return None, None

async def set_rss_cache(url: str, etag: str, last_modified: str):
    async with async_session() as session:
        cache = await session.get(RssCache, url)
        if cache:
            cache.etag = etag
            cache.last_modified = last_modified
            cache.cached_at = func.now()
        else:
            cache = RssCache(url=url, etag=etag, last_modified=last_modified)
            session.add(cache)
        await session.commit()
