import os
from dotenv import load_dotenv

load_dotenv()

# ===========================
# 🔑 Telegram Bot Settings
# ===========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CHANNEL_ID = os.getenv("CHANNEL_ID")  # ID канала для тестов и основной публикации

# ===========================
# 🤖 AI Provider: Groq
# ===========================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# ===========================
# 🤖 AI Provider: OpenAI
# ===========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ===========================
# 🤖 AI Provider: Anthropic
# ===========================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")

# ===========================
# 🗄️ Database & Redis
# ===========================
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# ===========================
# 📰 Default RSS Sources
# ===========================
DEFAULT_SOURCES = [
    {
        "name": "Xakep AI",
        "rss": "https://xakep.ru/tag/iskusstvennyj-intellekt/feed/",
        "keywords": "искусственный интеллект, нейросеть, машинное обучение, gpt, ai",
        "lang": "ru",
        "priority": "high",
    },
    {
        "name": "CNews AI",
        "rss": "https://www.cnews.ru/news/tech/ai/rss",
        "keywords": "искусственный интеллект, нейросеть, робот, автономный",
        "lang": "ru",
        "priority": "high",
    },
    {
        "name": "TechCrunch AI",
        "rss": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "keywords": "ai startup, funding, generative ai, llm, openai",
        "lang": "en",
        "priority": "high",
    },
    {
        "name": "ArXiv AI",
        "rss": "http://export.arxiv.org/rss/cs.AI",
        "keywords": "artificial intelligence, machine learning, neural, llm, research",
        "lang": "en",
        "priority": "medium",
    },
    {
        "name": "Google AI Blog",
        "rss": "https://blog.google/technology/ai/rss/",
        "keywords": "gemini, ai, model, research, google ai, deepmind",
        "lang": "en",
        "priority": "high",
    },
]

# ===========================
# 🔍 Global Keywords
# ===========================
ALL_KEYWORDS = [
    "нейросеть",
    "искусственный интеллект",
    "иИ",
    "машинное обучение",
    "gpt",
    "llm",
    "генеративный",
    "автоматизация",
    "ai",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "neural network",
    "transformer",
    "chatgpt",
    "openai",
    "anthropic",
    "gemini",
    "llama",
    "mistral",
]

# ===========================
# ⏱️ Scheduler Settings
# ===========================
POSTS_PER_DAY = 4
POST_INTERVAL_MIN = 300  # 5 часов
POST_INTERVAL_MAX = 360  # 6 часов

# ===========================
# 🎯 Content Settings
# ===========================
MIN_TITLE_LENGTH = 15
POST_STYLES = ["factual", "analytical", "practical", "news", "question"]

STYLE_EMOJIS = {
    "factual": "📊",
    "analytical": "🔍",
    "practical": "🛠️",
    "news": "⚡",
    "question": "❓",
}

# ===========================
# 💰 Subscription Prices (in Stars)
# ===========================
SUBSCRIPTION_PRICES = {
    "basic": {"stars": 500, "sources_limit": 5, "posts_per_day": 2, "name": "Базовый"},
    "pro": {"stars": 1500, "sources_limit": 15, "posts_per_day": 10, "name": "PRO"},
    "business": {
        "stars": 5000,
        "sources_limit": 50,
        "posts_per_day": 50,
        "name": "Business",
    },
}
