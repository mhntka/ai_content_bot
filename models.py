from sqlalchemy import (
    BigInteger,
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    subscription_status = Column(String, default="inactive")
    subscription_end = Column(DateTime, nullable=True)
    active_channel_id = Column(
        Integer, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, server_default=func.now())

    channels = relationship(
        "Channel", back_populates="user", foreign_keys="Channel.user_id"
    )
    active_channel = relationship("Channel", foreign_keys=[active_channel_id])


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False
    )
    tg_channel_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    ai_model = Column(String, default="groq")
    custom_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="channels", foreign_keys=[user_id])
    sources = relationship(
        "Source", back_populates="channel", cascade="all, delete-orphan"
    )
    drafts = relationship(
        "Draft", back_populates="channel", cascade="all, delete-orphan"
    )
    published_posts = relationship(
        "PublishedPost", back_populates="channel", cascade="all, delete-orphan"
    )
    scheduled_posts = relationship(
        "ScheduledPost", back_populates="channel", cascade="all, delete-orphan"
    )


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(
        Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String, nullable=False)
    rss_url = Column(String, nullable=False)
    keywords = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    lang = Column(String, default="ru")
    priority = Column(String, default="medium")
    created_at = Column(DateTime, server_default=func.now())

    channel = relationship("Channel", back_populates="sources")


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(
        Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False
    )
    source_url = Column(String, nullable=True)
    post_text = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    title = Column(String, nullable=True)
    source_name = Column(String, nullable=True)
    style = Column(String, nullable=True)
    status = Column(String, default="pending")
    scheduled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    channel = relationship("Channel", back_populates="drafts")
    scheduled_posts = relationship(
        "ScheduledPost", back_populates="draft", cascade="all, delete-orphan"
    )


class PublishedPost(Base):
    __tablename__ = "published_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(
        Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False
    )
    source_url = Column(String, nullable=False)
    published_at = Column(DateTime, server_default=func.now())

    channel = relationship("Channel", back_populates="published_posts")


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(
        Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False
    )
    draft_id = Column(
        Integer, ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())

    channel = relationship("Channel", back_populates="scheduled_posts")
    draft = relationship("Draft", back_populates="scheduled_posts")


class RssCache(Base):
    __tablename__ = "rss_cache"

    url = Column(String, primary_key=True)
    etag = Column(String, nullable=True)
    last_modified = Column(String, nullable=True)
    cached_at = Column(DateTime, server_default=func.now())
